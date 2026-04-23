"""
Horse Trackwork Scraper
For each horse found in race results, scrapes the full morning trackwork history
from HKJC (every training session recorded, including gallops, trotting, swimming, etc.)

Strategy:
  1. Load the horse profile page (Horse.aspx?HorseNo=XXXX)
  2. Find the "Trackwork Records" link from the navigation tabs
  3. Load that page and extract the full trackwork table

Output:
  horses/trackwork/trackwork_XXXX.csv   — full trackwork history per horse
"""

import os, re, time
import logging
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from scraper_utils import make_driver, load_page, safe_cell, log_failed, parse_zh_location
from comeback_detection import should_scrape
from lifecycle_helper import compute_last_race_dates, load_horse_state, load_today_entries

logging.basicConfig(level=logging.INFO, format="%(message)s")
PROFILES_FILE = os.path.join("horses", "profiles", "horse_profiles.csv")

RESULTS_DIR   = "data"
TRACKWORK_DIR = os.path.join("horses", "trackwork")
FAILED_LOG    = "failed_trackwork.log"
BASE_HORSE_URL = "https://racing.hkjc.com/racing/information/Chinese/Horse/Horse.aspx?HorseNo={horse_no}"

os.makedirs(TRACKWORK_DIR, exist_ok=True)

# ── 1. Collect unique horse numbers ─────────────────────────────────────────

def extract_horse_no(horse_name_str):
    m = re.search(r"\(([A-Z]\d+)\)", horse_name_str)
    return m.group(1) if m else None

print("Scanning race results for horse numbers...")
horse_nos = set()
for year in sorted(os.listdir(RESULTS_DIR)):
    year_path = os.path.join(RESULTS_DIR, year)
    if not os.path.isdir(year_path):
        continue
    for fname in os.listdir(year_path):
        if not fname.startswith("results_"):
            continue
        try:
            df = pd.read_csv(os.path.join(year_path, fname), encoding="utf-8-sig")
            for name in df["horse_name"].dropna():
                hno = extract_horse_no(str(name))
                if hno:
                    horse_nos.add(hno)
        except Exception:
            pass

print(f"Found {len(horse_nos)} unique horses.")

done = {f.replace("trackwork_", "").replace(".csv", "") for f in os.listdir(TRACKWORK_DIR) if f.endswith(".csv")}
todo_raw = sorted(horse_nos - done)
print(f"Already done: {len(done)} | Remaining (pre-filter): {len(todo_raw)}")

# ── Lifecycle filter: skip retired/inactive horses unless rescan due ────────
horse_state = load_horse_state(PROFILES_FILE)
last_race_dates = compute_last_race_dates(RESULTS_DIR)
today_entries = load_today_entries()
if today_entries:
    print(f"  Today's entry list: {len(today_entries)} horses (comeback override active)")
else:
    print("  Today's entry list: not available (comeback override inactive)")

todo = []
skipped_by_reason = {}
for hno in todo_raw:
    state = horse_state.get(hno, {})
    decision = should_scrape(
        hno,
        today_entries,
        current_status=state.get("status") or None,
        last_race_date=state.get("last_race_date") or last_race_dates.get(hno),
        profile_last_scraped=state.get("profile_last_scraped") or None,
    )
    if decision.should_scrape:
        todo.append(hno)
    else:
        skipped_by_reason[decision.reason] = skipped_by_reason.get(decision.reason, 0) + 1

skipped_total = sum(skipped_by_reason.values())
print(f"After lifecycle filter: {len(todo)} to scrape | {skipped_total} skipped")
for reason, count in sorted(skipped_by_reason.items()):
    print(f"  - skip[{reason}]: {count}")

if not todo:
    print("All horses already scraped.")
    exit(0)

# ── 2. Scrape ───────────────────────────────────────────────────────────────

driver = make_driver()

TRACKWORK_COLS = [
    "horse_no", "date", "work_type",
    "racecourse", "track", "workout_details", "gear"
]

for i, horse_no in enumerate(todo, 1):
    print(f"\n[{i}/{len(todo)}] Horse: {horse_no}")
    out_file = os.path.join(TRACKWORK_DIR, f"trackwork_{horse_no}.csv")

    # Load horse profile to find the trackwork link
    profile_url = BASE_HORSE_URL.format(horse_no=horse_no)
    if not load_page(driver, profile_url):
        log_failed(FAILED_LOG, horse_no, "profile page load failed")
        continue
    time.sleep(1)

    # Try to find a trackwork link on the page (either in tabs or in source)
    trackwork_url = None
    try:
        links = driver.find_elements(
            By.XPATH,
            "//a[contains(@href,'trackworkresult') or contains(translate(text(),'TRACKWORK','trackwork'),'trackwork')]"
        )
        for l in links:
            href = l.get_attribute("href") or ""
            if "trackworkresult" in href:
                trackwork_url = href
                break
    except Exception:
        pass

    if not trackwork_url:
        # Try extracting from page source directly
        src = driver.page_source
        m = re.search(r'href="([^"]*trackworkresult\?horseid=[^"]+)"', src)
        if m:
            trackwork_url = "https://racing.hkjc.com" + m.group(1) if m.group(1).startswith("/") else m.group(1)

    if not trackwork_url:
        print(f"  No trackwork URL found for {horse_no}")
        log_failed(FAILED_LOG, horse_no, "no trackwork URL")
        # Still save an empty file to avoid re-checking
        pd.DataFrame(columns=TRACKWORK_COLS).to_csv(out_file, index=False, encoding="utf-8-sig")
        continue

    print(f"  Trackwork URL: {trackwork_url}")
    if not load_page(driver, trackwork_url):
        log_failed(FAILED_LOG, horse_no, "trackwork page load failed")
        continue
    time.sleep(1)

    tables = driver.find_elements(By.TAG_NAME, "table")
    trackwork_table = None
    for t in tables:
        rows = t.find_elements(By.TAG_NAME, "tr")
        if rows and ("日期" in rows[0].text or "操練類型" in rows[0].text or "Date" in rows[0].text):
            trackwork_table = t
            break

    if not trackwork_table:
        print(f"  No trackwork table found")
        log_failed(FAILED_LOG, horse_no, "no trackwork table")
        pd.DataFrame(columns=TRACKWORK_COLS).to_csv(out_file, index=False, encoding="utf-8-sig")
        continue

    rows = trackwork_table.find_elements(By.TAG_NAME, "tr")
    records = []
    for row in rows[1:]:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) < 3:
            continue
        date_val = safe_cell(cells, 0)
        if not date_val or not re.match(r"\d{2}/\d{2}/\d{4}", date_val):
            continue
        work_type    = safe_cell(cells, 1)
        # Racecourse / Track split from cell 2
        location_raw = safe_cell(cells, 2)
        loc_parts    = location_raw.split(" ", 2)
        racecourse   = loc_parts[0] if loc_parts else ""
        track        = loc_parts[1] if len(loc_parts) > 1 else ""
        workout_det  = safe_cell(cells, 3)
        gear         = safe_cell(cells, 4)

        records.append({
            "horse_no":        horse_no,
            "date":            date_val,
            "work_type":       work_type,
            "racecourse":      racecourse,
            "track":           track,
            "workout_details": workout_det,
            "gear":            gear,
        })

    if records:
        pd.DataFrame(records)[TRACKWORK_COLS].to_csv(out_file, index=False, encoding="utf-8-sig")
        print(f"  Saved {len(records)} trackwork sessions")
    else:
        print(f"  No trackwork records found")
        pd.DataFrame(columns=TRACKWORK_COLS).to_csv(out_file, index=False, encoding="utf-8-sig")

driver.quit()
print("\nHorse trackwork scraping complete!")
