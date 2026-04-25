"""
Horse Profile Scraper
Reads all saved race results CSVs to build a list of unique horses, then
scrapes each horse's full profile, pedigree, and form records from HKJC.

Output:
  horses/profiles/horse_profiles.csv      — one row per horse (profile + pedigree)
  horses/form_records/form_XXXX.csv       — full race history per horse
"""

import os, re, time
import argparse
import zlib
import logging
from datetime import date
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from scraper_utils import make_driver, load_page, safe_cell, log_failed, parse_zh_location
from comeback_detection import should_scrape, classify_status
from lifecycle_helper import (
    compute_last_race_dates, backfill_lifecycle, load_horse_state, load_today_entries,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")

# ── CLI: shard control for parallel GHA matrix runs ─────────────────────────
# When --total-shards > 1, filter the horse_no set to only those matching
# CRC32(horse_no) % total_shards == shard. Deterministic across runners
# (unlike Python's hash() which is PYTHONHASHSEED-randomized).
_ap = argparse.ArgumentParser()
_ap.add_argument("--shard", type=int, default=0,
                 help="Shard index (0..total_shards-1) for matrix runs.")
_ap.add_argument("--total-shards", type=int, default=1,
                 help="Total shard count. 1 = no sharding (full pass).")
_ARGS = _ap.parse_args()

RESULTS_DIR  = "data"
PROFILES_DIR = os.path.join("horses", "profiles")
FORM_DIR     = os.path.join("horses", "form_records")
FAILED_LOG   = "failed_horses.log"
BASE_HORSE_URL = "https://racing.hkjc.com/racing/information/Chinese/Horse/Horse.aspx?HorseNo={horse_no}"

os.makedirs(PROFILES_DIR, exist_ok=True)
os.makedirs(FORM_DIR, exist_ok=True)

# ── 1. Collect all unique horse numbers from saved results ──────────────────

def extract_horse_no(horse_name_str):
    """Extract code like 'S246' or 'H436' from 'DOUBLE POINT (S246)'."""
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
        except Exception as e:
            print(f"  Error reading {fname}: {e}")

print(f"Found {len(horse_nos)} unique horses.")

# ── Shard filter (GHA matrix) — partition by CRC32(horse_no) ────────────────
if _ARGS.total_shards > 1:
    before = len(horse_nos)
    horse_nos = {h for h in horse_nos
                 if zlib.crc32(h.encode()) % _ARGS.total_shards == _ARGS.shard}
    print(f"Shard {_ARGS.shard}/{_ARGS.total_shards}: filtered {before} → {len(horse_nos)} horses")

# ── 2. Determine which horses still need scraping ───────────────────────────

profiles_file = os.path.join(PROFILES_DIR, "horse_profiles.csv")

# ── Lifecycle backfill: compute last_race_date for every horse from the
#    race result CSVs, then ensure horse_profiles.csv has the 3 lifecycle
#    columns populated for every existing row.
print("Computing last race dates from results CSVs...")
last_race_dates = compute_last_race_dates(RESULTS_DIR)
print(f"  Got last_race_date for {len(last_race_dates)} horses")

if os.path.exists(profiles_file):
    backfill_lifecycle(profiles_file, last_race_dates)
    print("  Lifecycle columns backfilled in horse_profiles.csv")

horse_state = load_horse_state(profiles_file)

# Today's HKJC entry list (排位表). Produced by EntryList_Scraper.py,
# consumed here to fire the comeback override on retired/inactive horses
# that re-appear in today's draw. Empty set => no override; quarterly
# safety net still applies.
today_entries = load_today_entries()
if today_entries:
    print(f"  Today's entry list: {len(today_entries)} horses (comeback override active)")
else:
    print("  Today's entry list: not available (comeback override inactive)")

# ── Decide which horses to (re)scrape using comeback_detection ──────────────
todo = []
skipped_by_reason = {}
for hno in sorted(horse_nos):
    state = horse_state.get(hno, {})
    decision = should_scrape(
        hno,
        today_entries,
        current_status=state.get("status") or None,
        last_race_date=state.get("last_race_date") or last_race_dates.get(hno),
        profile_last_scraped=state.get("profile_last_scraped") or None,
    )
    if decision.should_scrape:
        todo.append((hno, decision))
    else:
        skipped_by_reason[decision.reason] = skipped_by_reason.get(decision.reason, 0) + 1

skipped_total = sum(skipped_by_reason.values())
print(f"To scrape: {len(todo)} | Skipped by lifecycle filter: {skipped_total}")
for reason, count in sorted(skipped_by_reason.items()):
    print(f"  - skip[{reason}]: {count}")

if not todo:
    print("All horses already scraped.")
    exit(0)

# ── 3. Scrape ───────────────────────────────────────────────────────────────

driver = make_driver()
all_profiles = []

FORM_COLS = [
    "horse_no", "race_index", "place", "date",
    "racecourse", "track", "course",
    "distance_m", "going", "race_class",
    "draw", "rating", "trainer", "jockey",
    "lbw", "win_odds", "actual_wt_lbs",
    "running_position", "finish_time",
    "declared_wt_lbs", "gear"
]

today_iso = date.today().isoformat()

for i, (horse_no, decision) in enumerate(todo, 1):
    print(f"\n[{i}/{len(todo)}] Horse: {horse_no} ({decision.reason})")
    form_out = os.path.join(FORM_DIR, f"form_{horse_no}.csv")

    url = BASE_HORSE_URL.format(horse_no=horse_no)
    if not load_page(driver, url):
        log_failed(FAILED_LOG, horse_no, "page load failed")
        continue

    time.sleep(1)
    tables = driver.find_elements(By.TAG_NAME, "table")
    if len(tables) < 5:
        print(f"  No data (page may be empty)")
        log_failed(FAILED_LOG, horse_no, "no tables found")
        continue

    # ── Profile info ──────────────────────────────────────────────────────

    profile = {
        "horse_no": horse_no,
        "name": "",
        "last_race_date": last_race_dates.get(horse_no, ""),
        "status": decision.new_status or classify_status(last_race_dates.get(horse_no)),
        "profile_last_scraped": today_iso,
    }

    # Horse name from header
    try:
        name_el = driver.find_element(By.XPATH, "//table[@class='horseProfile']//tr[1]//td[1]")
        raw = name_el.text.strip().split("\n")[0]
        profile["name"] = raw
    except Exception:
        pass

    # Table 3: Country, Color/Sex, Import Type, Total Stakes, Win record
    try:
        t3 = tables[3].find_elements(By.TAG_NAME, "tr")
        for row in t3:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 3:
                key = cells[0].text.strip().lower().replace(" ", "_").replace("/", "_").replace(".", "").replace("*", "")
                val = cells[2].text.strip()
                profile[key] = val
    except Exception as e:
        print(f"  Warning (table3): {e}")

    # Table 4: Owner, Rating, Sire, Dam, Dam's Sire (pedigree)
    try:
        t4 = tables[4].find_elements(By.TAG_NAME, "tr")
        for row in t4:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 3:
                key = cells[0].text.strip().lower().replace(" ", "_").replace("'", "").replace("/", "_")
                val = cells[2].text.strip().split("\n")[0]  # first line only for 'Same Sire'
                profile[key] = val
    except Exception as e:
        print(f"  Warning (table4): {e}")

    all_profiles.append(profile)
    print(f"  Profile: {profile.get('name', '?')} | Sire: {profile.get('sire', '?')} | Dam: {profile.get('dam', '?')}")

    # ── Form Records ─────────────────────────────────────────────────────

    if os.path.exists(form_out):
        print(f"  Form records already saved, skipping")
        continue

    try:
        form_table = None
        for t in tables:
            cls = t.get_attribute("class") or ""
            if "bigborder" in cls:
                form_table = t
                break
        if not form_table:
            print(f"  No form table found")
            continue

        rows = form_table.find_elements(By.TAG_NAME, "tr")
        form_rows = []
        for row in rows[1:]:  # skip header
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 10 or not cells[0].text.strip().isdigit():
                continue
            # Parse RC/Track/Course: Chinese format e.g. '沙田草地"A"'
            rc, track, course = parse_zh_location(safe_cell(cells, 3))

            form_rows.append({
                "horse_no":         horse_no,
                "race_index":       safe_cell(cells, 0),
                "place":            safe_cell(cells, 1),
                "date":             safe_cell(cells, 2),
                "racecourse":       rc,
                "track":            track,
                "course":           course,
                "distance_m":       safe_cell(cells, 4),
                "going":            safe_cell(cells, 5),
                "race_class":       safe_cell(cells, 6),
                "draw":             safe_cell(cells, 7),
                "rating":           safe_cell(cells, 8),
                "trainer":          safe_cell(cells, 9),
                "jockey":           safe_cell(cells, 10),
                "lbw":              safe_cell(cells, 11),
                "win_odds":         safe_cell(cells, 12),
                "actual_wt_lbs":    safe_cell(cells, 13),
                "running_position": safe_cell(cells, 14),
                "finish_time":      safe_cell(cells, 15),
                "declared_wt_lbs":  safe_cell(cells, 16),
                "gear":             safe_cell(cells, 17),
            })

        if form_rows:
            pd.DataFrame(form_rows)[FORM_COLS].to_csv(form_out, index=False, encoding="utf-8-sig")
            print(f"  Form records: {len(form_rows)} runs saved")
        else:
            print(f"  No form records found")

    except Exception as e:
        print(f"  Error extracting form records: {e}")

    # Save profiles incrementally every 20 horses.
    # keep='last' so a rescan row replaces the prior one (lifecycle fields update).
    if i % 20 == 0 and all_profiles:
        df = pd.DataFrame(all_profiles)
        if os.path.exists(profiles_file):
            existing = pd.read_csv(profiles_file, encoding="utf-8-sig")
            df = pd.concat([existing, df], ignore_index=True).drop_duplicates(
                subset="horse_no", keep="last"
            )
        df.to_csv(profiles_file, index=False, encoding="utf-8-sig")
        all_profiles = []
        print(f"  [Checkpoint] Profiles saved.")

# Final save
if all_profiles:
    df = pd.DataFrame(all_profiles)
    if os.path.exists(profiles_file):
        existing = pd.read_csv(profiles_file, encoding="utf-8-sig")
        df = pd.concat([existing, df], ignore_index=True).drop_duplicates(
            subset="horse_no", keep="last"
        )
    df.to_csv(profiles_file, index=False, encoding="utf-8-sig")

driver.quit()
print("\nHorse profile scraping complete!")
