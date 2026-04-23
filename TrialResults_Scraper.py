"""
HKJC Trial Results Scraper — Traditional Chinese
Scrapes all available trial result sessions from:
  https://racing.hkjc.com/zh-hk/local/information/btresult

Output:
  trials/trial_results.csv  — all trial groups, one row per horse
  trials/trial_sessions.csv — summary of each trial session (group-level)

Columns (trial_results.csv):
  trial_date, group_no, trial_venue, distance_m, going, group_time,
  group_sectional_times, horse_name, horse_no, jockey, trainer,
  draw, gear, lbw, running_position, finish_time, result, commentary
"""

import os, re, time
import pandas as pd
from selenium.webdriver.common.by import By
from scraper_utils import make_driver, load_page, safe_cell, log_failed

TRIAL_URL   = "https://racing.hkjc.com/zh-hk/local/information/btresult"
OUTPUT_DIR  = "trials"
FAILED_LOG  = "failed_trials.log"
RESULTS_OUT = os.path.join(OUTPUT_DIR, "trial_results.csv")
SESSION_OUT = os.path.join(OUTPUT_DIR, "trial_sessions.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

driver = make_driver()

# ── 1. Get all available trial dates ─────────────────────────────────────────

print("Loading trial results page to discover available dates...")
if not load_page(driver, TRIAL_URL):
    print("Failed to load trial results page.")
    driver.quit()
    exit(1)

time.sleep(2)

# Read available dates from the dropdown
available_dates = []
try:
    links = driver.find_elements(
        By.XPATH,
        "//select//option | //a[contains(@href,'btresult')]"
    )
except Exception:
    links = []

# Try the date dropdown/list
date_opts = driver.find_elements(By.XPATH, "//select/option")
if date_opts:
    for o in date_opts:
        v = o.get_attribute("value") or ""
        t = o.text.strip()
        if re.match(r"\d{2}/\d{2}/\d{4}", t):
            available_dates.append(t)
    print(f"Found {len(available_dates)} trial dates from dropdown.")

# Also try reading the date list from the sidebar
if not available_dates:
    body_text = driver.find_element(By.TAG_NAME, "body").text
    date_matches = re.findall(r"\b(\d{2}/\d{2}/\d{4})\b", body_text)
    available_dates = sorted(set(date_matches), reverse=True)
    print(f"Found {len(available_dates)} trial dates from page text.")

if not available_dates:
    print("No trial dates found. Exiting.")
    driver.quit()
    exit(0)

print(f"Trial dates: {available_dates[:5]} ... {available_dates[-5:]}")

# ── 2. Determine what's already scraped ──────────────────────────────────────

done_dates = set()
if os.path.exists(RESULTS_OUT):
    try:
        existing = pd.read_csv(RESULTS_OUT, encoding="utf-8-sig")
        done_dates = set(existing["trial_date"].astype(str))
        print(f"Already scraped: {len(done_dates)} trial dates")
    except Exception:
        pass

todo = [d for d in available_dates if d not in done_dates]
print(f"Remaining to scrape: {len(todo)} trial dates")

# ── 3. Scrape each trial date ─────────────────────────────────────────────────

all_horse_rows  = []
all_session_rows= []


def parse_group_info(table):
    """Extract venue, distance, going, time, sectional times from group header."""
    rows = table.find_elements(By.TAG_NAME, "tr")
    info = {
        "trial_venue": "", "distance_m": "", "going": "",
        "group_time": "", "group_sectional_times": ""
    }
    for row in rows:
        text = row.text.strip()
        # "第 1 組 - 從化草地 - 1000米"
        m = re.match(r"第\s*(\d+)\s*組\s*-\s*(.+?)\s*-\s*(\d+)米", text)
        if m:
            info["trial_venue"] = m.group(2).strip()
            info["distance_m"]  = m.group(3).strip()
        # "場地狀況: 好地       時間: 0.58.70"
        m2 = re.search(r"場地狀況[:：]\s*([^\s]+)\s+時間[:：]\s*([\d.:]+)", text)
        if m2:
            info["going"]      = m2.group(1).strip()
            info["group_time"] = m2.group(2).strip()
        # "分段時間: 13.8   21.8   23.1"
        m3 = re.search(r"分段時間[:：]\s*(.+)", text)
        if m3:
            info["group_sectional_times"] = m3.group(1).strip()
    return info


def parse_group_horses(table, trial_date, group_no, group_info):
    """Parse the bigborder horse table for one trial group."""
    rows = table.find_elements(By.TAG_NAME, "tr")
    records = []
    for row in rows[1:]:  # skip header
        cells = row.find_elements(By.TAG_NAME, "td")
        if not cells:
            continue
        # Horse name cell might contain "馬名 (HorseNo)" or just "馬名 (XXXX)"
        horse_raw = safe_cell(cells, 0)
        if not horse_raw or horse_raw.startswith("馬名"):
            continue
        hm = re.search(r"\(([A-Z0-9]+)\)", horse_raw)
        horse_no   = hm.group(1) if hm else ""
        horse_name = re.sub(r"\s*\([^)]+\)\s*$", "", horse_raw).strip()

        records.append({
            "trial_date":            trial_date,
            "group_no":              group_no,
            "trial_venue":           group_info["trial_venue"],
            "distance_m":            group_info["distance_m"],
            "going":                 group_info["going"],
            "group_time":            group_info["group_time"],
            "group_sectional_times": group_info["group_sectional_times"],
            "horse_name":            horse_name,
            "horse_no":              horse_no,
            "jockey":                safe_cell(cells, 1),
            "trainer":               safe_cell(cells, 2),
            "draw":                  safe_cell(cells, 3),
            "gear":                  safe_cell(cells, 4),
            "lbw":                   safe_cell(cells, 5),
            "running_position":      safe_cell(cells, 6),
            "finish_time":           safe_cell(cells, 7),
            "result":                safe_cell(cells, 8),
            "commentary":            safe_cell(cells, 9) if len(cells) > 9 else "",
        })
    return records


for i, trial_date in enumerate(todo, 1):
    print(f"\n[{i}/{len(todo)}] Trial date: {trial_date}")
    # Convert DD/MM/YYYY -> YYYYMMDD for URL
    parts = trial_date.split("/")
    date_compact = parts[2] + parts[1] + parts[0]  # YYYYMMDD
    url = f"{TRIAL_URL}?searchDate={date_compact}"

    if not load_page(driver, url):
        log_failed(FAILED_LOG, trial_date, "page load failed")
        continue
    time.sleep(1.5)

    tables = driver.find_elements(By.TAG_NAME, "table")
    if not tables:
        print(f"  No tables found")
        log_failed(FAILED_LOG, trial_date, "no tables")
        continue

    # Tables alternate: group_info_table, (sub_table), horse_table, group_info_table, ...
    group_no    = 0
    current_info= {}
    date_horses = []
    date_sessions = []

    j = 0
    while j < len(tables):
        t = tables[j]
        rows = t.find_elements(By.TAG_NAME, "tr")
        if not rows:
            j += 1
            continue
        cls = t.get_attribute("class") or ""
        header_text = rows[0].text.strip() if rows else ""

        # Detect group header table: "第 N 組 - ..."
        if re.match(r"第\s*\d+\s*組", header_text):
            group_no += 1
            current_info = parse_group_info(t)
            date_sessions.append({
                "trial_date": trial_date,
                "group_no":   group_no,
                **current_info
            })
            j += 1
            continue

        # Detect horse data table (bigborder class)
        if "bigborder" in cls and group_no > 0:
            horse_rows = parse_group_horses(t, trial_date, group_no, current_info)
            date_horses.extend(horse_rows)
            print(f"  Group {group_no}: {len(horse_rows)} horses "
                  f"({current_info.get('trial_venue','')} {current_info.get('distance_m','')}米)")
            j += 1
            continue

        j += 1

    all_horse_rows.extend(date_horses)
    all_session_rows.extend(date_sessions)

    # Save incrementally every 10 dates
    if i % 10 == 0 and all_horse_rows:
        df_h = pd.DataFrame(all_horse_rows)
        df_s = pd.DataFrame(all_session_rows)
        if os.path.exists(RESULTS_OUT):
            existing_h = pd.read_csv(RESULTS_OUT, encoding="utf-8-sig")
            df_h = pd.concat([existing_h, df_h], ignore_index=True).drop_duplicates()
        if os.path.exists(SESSION_OUT):
            existing_s = pd.read_csv(SESSION_OUT, encoding="utf-8-sig")
            df_s = pd.concat([existing_s, df_s], ignore_index=True).drop_duplicates()
        df_h.to_csv(RESULTS_OUT, index=False, encoding="utf-8-sig")
        df_s.to_csv(SESSION_OUT, index=False, encoding="utf-8-sig")
        all_horse_rows  = []
        all_session_rows= []
        print(f"  [Checkpoint] 試閘資料已儲存")

# ── 4. Final save ─────────────────────────────────────────────────────────────

if all_horse_rows or all_session_rows:
    df_h = pd.DataFrame(all_horse_rows) if all_horse_rows else pd.DataFrame()
    df_s = pd.DataFrame(all_session_rows) if all_session_rows else pd.DataFrame()
    if not df_h.empty:
        if os.path.exists(RESULTS_OUT):
            existing_h = pd.read_csv(RESULTS_OUT, encoding="utf-8-sig")
            df_h = pd.concat([existing_h, df_h], ignore_index=True).drop_duplicates()
        df_h.to_csv(RESULTS_OUT, index=False, encoding="utf-8-sig")
    if not df_s.empty:
        if os.path.exists(SESSION_OUT):
            existing_s = pd.read_csv(SESSION_OUT, encoding="utf-8-sig")
            df_s = pd.concat([existing_s, df_s], ignore_index=True).drop_duplicates()
        df_s.to_csv(SESSION_OUT, index=False, encoding="utf-8-sig")

driver.quit()
print("\n試閘結果擷取完成！")
