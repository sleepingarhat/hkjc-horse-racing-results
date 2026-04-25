"""
Trainer Data Scraper
Scrapes all trainer profiles and full past race records from HKJC.

Steps:
  1. Load the Trainer Ranking page to get all trainer name→code mappings
  2. For each trainer, scrape profile stats and full past records

Output:
  trainers/trainer_profiles.csv          — one row per trainer (stats summary)
  trainers/records/trainer_CODE.csv      — full past race records per trainer
"""

import os, re, time
import pandas as pd
from selenium.webdriver.common.by import By
from scraper_utils import make_driver, load_page, safe_cell, log_failed, parse_zh_location

PROFILES_DIR = "trainers"
RECORDS_DIR  = os.path.join("trainers", "records")
FAILED_LOG   = "failed_trainers.log"

RANKING_URL  = "https://racing.hkjc.com/zh-hk/local/info/trainer-ranking"
PROFILE_URL  = "https://racing.hkjc.com/zh-hk/local/information/trainerprofile?trainerid={code}&season={season}"
SEASONS      = ["Current", "Previous"]

os.makedirs(PROFILES_DIR, exist_ok=True)
os.makedirs(RECORDS_DIR, exist_ok=True)

# ── 1. Get all trainer codes ─────────────────────────────────────────────────

driver = make_driver()
print("Loading trainer ranking page...")
if not load_page(driver, RANKING_URL):
    print("Failed to load trainer ranking.")
    driver.quit()
    exit(1)

time.sleep(2)
trainers = {}  # code -> name

for season_btn_text in ["今季資料", "上季資料", "Current Season", "Previous Season"]:
    # Try clicking season toggle (Chinese: 今季資料 / 上季資料)
    try:
        btn = driver.find_element(By.XPATH, f"//a[contains(text(),'{season_btn_text}')]")
        btn.click()
        time.sleep(2)
    except Exception:
        pass

    links = driver.find_elements(
        By.XPATH,
        "//table//a[contains(@href,'trainerprofile') or contains(@href,'trainerpastrec')]"
    )
    for l in links:
        href = l.get_attribute("href") or ""
        m = re.search(r"trainerid=([A-Z]+)", href, re.IGNORECASE)
        if m:
            code = m.group(1).upper()
            name = l.text.strip()
            if name and code not in trainers:
                trainers[code] = name

print(f"Found {len(trainers)} trainers")

profiles_file = os.path.join(PROFILES_DIR, "trainer_profiles.csv")
done = set()
if os.path.exists(profiles_file):
    try:
        _existing = pd.read_csv(profiles_file, encoding="utf-8-sig")
        _before = len(_existing)
        _existing["trainer_code"] = _existing["trainer_code"].astype(str).str.strip()
        _existing = _existing.drop_duplicates(subset="trainer_code", keep="last")
        if len(_existing) != _before:
            _existing.to_csv(profiles_file, index=False, encoding="utf-8-sig")
            print(f"[trainer-dedup] cleaned {_before} -> {len(_existing)} rows")
        done = set(_existing["trainer_code"])
    except Exception as e:
        print(f"[trainer-dedup] skip: {e}")

todo = [
    c for c in trainers
    if c not in done
    or not os.path.exists(os.path.join(RECORDS_DIR, f"trainer_{c}.csv"))
]
print(f"Profiles already scraped: {len(done)} | "
      f"To process (missing profile OR missing records): {len(todo)}")

# ── 2. Scrape ────────────────────────────────────────────────────────────────

RECORD_COLS = [
    "trainer_code", "trainer_name", "season",
    "race_index", "place", "total_starters",
    "date", "venue", "track", "course",
    "distance_m", "race_class", "going",
    "horse_name", "horse_no", "draw", "rating",
    "jockey", "gear", "actual_wt_lbs", "win_odds"
]

all_profiles = []

for i, code in enumerate(todo, 1):
    name = trainers[code]
    print(f"\n[{i}/{len(todo)}] Trainer: {name} ({code})")
    records_file = os.path.join(RECORDS_DIR, f"trainer_{code}.csv")

    all_records = []
    profile = {"trainer_code": code, "trainer_name": name}

    for season in SEASONS:
        url = PROFILE_URL.format(code=code, season=season)
        if not load_page(driver, url):
            log_failed(FAILED_LOG, code, f"load failed season={season}")
            continue
        time.sleep(1)

        tables = driver.find_elements(By.TAG_NAME, "table")
        if not tables:
            continue

        # Stats (Table 0)
        try:
            for row in tables[0].find_elements(By.TAG_NAME, "tr"):
                for chunk in row.text.split("  "):
                    if ":" in chunk:
                        parts = chunk.split(":", 1)
                        key = parts[0].strip().lower().replace(" ", "_").replace(".", "").replace("#", "no")
                        val = parts[1].strip()
                        profile[f"{season.lower()}_{key}"] = val
        except Exception as e:
            print(f"  Warning (stats): {e}")

        # Records (Table 1+)
        try:
            rec_table = None
            for t in tables:
                rows = t.find_elements(By.TAG_NAME, "tr")
                if rows and len(rows) > 5:
                    header = rows[0].text
                    if "馬名" in header or "場次" in header or "Horse" in header or "Race" in header:
                        rec_table = t
                        break
            if not rec_table:
                continue

            current_date = ""
            current_venue = ""
            for row in rec_table.find_elements(By.TAG_NAME, "tr")[1:]:
                cells = row.find_elements(By.TAG_NAME, "td")
                if not cells:
                    continue

                # Date/venue header row (merged cell)
                if len(cells) <= 2:
                    txt = cells[0].text.strip()
                    m = re.match(r"(\d{2}/\d{2}/\d{4})\s+(.+)", txt)
                    if m:
                        current_date = m.group(1)
                        current_venue = m.group(2).split("\n")[0].strip()
                    continue

                # Skip non-data rows
                if not safe_cell(cells, 0).isdigit():
                    continue

                placing_raw = safe_cell(cells, 1)
                place, total = "", ""
                if "/" in placing_raw:
                    parts = placing_raw.split("/", 1)
                    place = parts[0].strip()
                    total = parts[1].strip()
                else:
                    place = placing_raw

                # Track/Course: Chinese format e.g. '草地"C"'
                _, track, course = parse_zh_location(safe_cell(cells, 2))

                # Horse name may have horse no in parens: "DOUBLE POINT (S246)"
                horse_raw = safe_cell(cells, 5)
                hm = re.search(r"\(([A-Z]\d+)\)", horse_raw)
                horse_no_extracted = hm.group(1) if hm else ""
                horse_name_clean = re.sub(r"\s*\([A-Z]\d+\)", "", horse_raw).strip()

                all_records.append({
                    "trainer_code":   code,
                    "trainer_name":   name,
                    "season":         season,
                    "race_index":     safe_cell(cells, 0),
                    "place":          place,
                    "total_starters": total,
                    "date":           current_date,
                    "venue":          current_venue,
                    "track":          track,
                    "course":         course,
                    "distance_m":     safe_cell(cells, 3),
                    "race_class":     safe_cell(cells, 4),
                    "going":          safe_cell(cells, 5) if len(cells) <= 8 else "",
                    "horse_name":     horse_name_clean,
                    "horse_no":       horse_no_extracted,
                    "draw":           safe_cell(cells, 7),
                    "rating":         safe_cell(cells, 8),
                    "jockey":         safe_cell(cells, 9),
                    "gear":           safe_cell(cells, 10),
                    "actual_wt_lbs":  safe_cell(cells, 11),
                    "win_odds":       safe_cell(cells, 12),
                })
        except Exception as e:
            print(f"  Warning (records season={season}): {e}")

    all_profiles.append(profile)
    print(f"  Trainer {name}: {len(all_records)} race records")

    if all_records and not os.path.exists(records_file):
        pd.DataFrame(all_records).to_csv(records_file, index=False, encoding="utf-8-sig")

    if i % 10 == 0 and all_profiles:
        df = pd.DataFrame(all_profiles)
        if os.path.exists(profiles_file):
            existing = pd.read_csv(profiles_file, encoding="utf-8-sig")
            df = pd.concat([existing, df], ignore_index=True).drop_duplicates(subset="trainer_code", keep="last")
        df.to_csv(profiles_file, index=False, encoding="utf-8-sig")
        all_profiles = []
        print("  [Checkpoint] Saved.")

if all_profiles:
    df = pd.DataFrame(all_profiles)
    if os.path.exists(profiles_file):
        existing = pd.read_csv(profiles_file, encoding="utf-8-sig")
        df = pd.concat([existing, df], ignore_index=True).drop_duplicates(subset="trainer_code", keep="last")
    df.to_csv(profiles_file, index=False, encoding="utf-8-sig")

driver.quit()
print("\nTrainer data scraping complete!")
