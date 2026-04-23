"""
HKJC Fixture Calendar Scraper — extracts annual race-day calendar.

Source: https://racing.hkjc.com/racing/information/Chinese/Racing/Fixture.aspx?calyear=Y&calmonth=M

Key insight: the calendar IS rendered server-side (no JS needed).
Race-day cells are <td class="calendar">DD ...</td>.
Non-race weekdays are <td class="font_wb ">DD</td>.
Other-month fillers are <td class="color_H font_wb">DD</td>.

We fetch each month with httpx and regex-extract td.calendar cells.

Output: data/fixtures/fixtures.csv with columns:
    date (YYYY-MM-DD), season_year, month, day, weekday, captured_at

Run:
    python FixtureCalendar_Scraper.py                 # current year + next year
    python FixtureCalendar_Scraper.py --year 2026     # specific year
    python FixtureCalendar_Scraper.py --years 2025,2026
"""

import argparse
import os
import re
import sys
from datetime import date, datetime, timezone
from typing import List, Dict

import httpx
import pandas as pd

FIXTURE_URL = "https://racing.hkjc.com/racing/information/Chinese/Racing/Fixture.aspx"
OUTPUT_DIR = os.path.join("data", "fixtures")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "fixtures.csv")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
}

# Race-day cells look like:
#   <td class="calendar">
#       <p class="f_clear">
#           <span class="f_fl f_fs14">DD</span>
#           ...venue images...
# The day number lives in the first <span class="f_fl ..."> inside a td.calendar.
CALENDAR_RE = re.compile(
    r'<td[^>]*class="calendar"[^>]*>\s*<p[^>]*>\s*<span[^>]*class="f_fl[^"]*"[^>]*>\s*(\d{1,2})\s*</span>',
    re.IGNORECASE | re.DOTALL,
)


def fetch_month(client: httpx.Client, year: int, month: int) -> List[int]:
    """Return list of race-day day-of-month integers for the given (year, month)."""
    url = f"{FIXTURE_URL}?calyear={year}&calmonth={month:02d}"
    r = client.get(url, timeout=20.0)
    r.raise_for_status()
    days = [int(d) for d in CALENDAR_RE.findall(r.text)]
    return sorted({d for d in days if 1 <= d <= 31})


def scrape_year(year: int) -> List[Dict]:
    rows: List[Dict] = []
    captured = datetime.now(timezone.utc).isoformat()
    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        for month in range(1, 13):
            try:
                days = fetch_month(client, year, month)
            except Exception as e:
                print(f"[fixture] {year}-{month:02d} error: {e}", file=sys.stderr)
                continue
            print(f"[fixture] {year}-{month:02d}  race days: {days}")
            for d in days:
                try:
                    dt = date(year, month, d)
                except ValueError:
                    continue
                rows.append({
                    "date": dt.isoformat(),
                    "season_year": year,
                    "month": month,
                    "day": d,
                    "weekday": dt.strftime("%a"),
                    "captured_at": captured,
                })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--years", type=str, default=None, help="comma-separated years")
    args = ap.parse_args()

    today = date.today()
    if args.years:
        years = [int(y) for y in args.years.split(",") if y.strip()]
    elif args.year:
        years = [args.year]
    else:
        years = [today.year, today.year + 1]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_rows: List[Dict] = []
    for y in years:
        all_rows.extend(scrape_year(y))

    if not all_rows:
        print("[fixture] WARN: zero dates scraped — keeping existing cache untouched",
              file=sys.stderr)
        sys.exit(1)

    df_new = pd.DataFrame(all_rows).drop_duplicates(subset=["date"]).sort_values("date")

    # Merge with existing cache — keep dates outside scraped year range
    if os.path.exists(OUTPUT_CSV):
        df_old = pd.read_csv(OUTPUT_CSV)
        years_set = set(years)
        df_keep = df_old[~df_old["season_year"].isin(years_set)]
        df_final = pd.concat([df_keep, df_new], ignore_index=True).drop_duplicates(subset=["date"]).sort_values("date")
    else:
        df_final = df_new

    df_final.to_csv(OUTPUT_CSV, index=False)
    print(f"[fixture] wrote {len(df_final)} total rows ({len(df_new)} new) -> {OUTPUT_CSV}")

    # Also emit per-year file for convenience
    for y in years:
        sub = df_final[df_final["season_year"] == y]
        per = os.path.join(OUTPUT_DIR, f"{y}_fixtures.csv")
        sub.to_csv(per, index=False)
        print(f"[fixture] wrote {len(sub)} rows -> {per}")


if __name__ == "__main__":
    main()
