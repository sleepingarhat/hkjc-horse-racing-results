"""CSV-based lifecycle state helpers for HKJC scrapers."""
import os
import re
from datetime import date
import pandas as pd

from comeback_detection import classify_status

LIFECYCLE_COLS = ["last_race_date", "status", "profile_last_scraped"]
HORSE_NO_RE = re.compile(r"\(([A-Z]\d+)\)")


def compute_last_race_dates(results_dir="data"):
    """Scan all results_*.csv under results_dir/<year>/ and return
    {horse_no: 'YYYY-MM-DD'} mapping each horse to its most recent race date."""
    last = {}
    if not os.path.isdir(results_dir):
        return last
    for year in sorted(os.listdir(results_dir)):
        ypath = os.path.join(results_dir, year)
        if not os.path.isdir(ypath):
            continue
        for fname in os.listdir(ypath):
            if not fname.startswith("results_") or not fname.endswith(".csv"):
                continue
            try:
                df = pd.read_csv(
                    os.path.join(ypath, fname),
                    encoding="utf-8-sig",
                    usecols=["date", "horse_name"],
                )
            except Exception:
                continue
            for _, row in df.iterrows():
                m = HORSE_NO_RE.search(str(row["horse_name"]))
                if not m:
                    continue
                hno = m.group(1)
                d = str(row["date"])[:10]
                if hno not in last or d > last[hno]:
                    last[hno] = d
    return last


def backfill_lifecycle(profiles_csv, last_race_dates, today=None):
    """Ensure horse_profiles.csv has the 3 lifecycle columns populated:
       last_race_date (from results), status (classified), profile_last_scraped
       (preserved if present, else blank).
    Returns the updated DataFrame, or None if file missing.
    """
    if not os.path.exists(profiles_csv):
        return None
    df = pd.read_csv(profiles_csv, encoding="utf-8-sig")
    for col in LIFECYCLE_COLS:
        if col not in df.columns:
            df[col] = ""
    df["last_race_date"] = df["horse_no"].astype(str).map(
        lambda h: last_race_dates.get(h, "")
    )
    df["status"] = df["last_race_date"].map(lambda d: classify_status(d, today))
    # Rows that already exist here have data from a prior scrape; treat their
    # profile as fresh-as-of today so the lifecycle filter doesn't re-scrape
    # everyone on first run. Quarterly/monthly rescan rules will fire later.
    today_iso = (today or date.today()).isoformat()
    df["profile_last_scraped"] = df["profile_last_scraped"].fillna("").replace(
        "", today_iso
    )
    df.to_csv(profiles_csv, index=False, encoding="utf-8-sig")
    return df


def load_today_entries(entries_dir="entries", today=None):
    """Read entries/today_entries.txt produced by EntryList_Scraper.

    Returns a set of horse codes. Returns empty set if:
      - file is missing
      - file has no header (legacy/unsafe)
      - meeting date in header has already passed (stale)
      - file is a fail-closed sentinel (header starts with '# stale')
    """
    path = os.path.join(entries_dir, "today_entries.txt")
    if not os.path.exists(path):
        return set()
    today = today or date.today()
    codes = set()
    meeting_ok = False
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            if ln.startswith("#"):
                if "stale" in ln:
                    return set()
                m = re.search(r"meeting=(\d{4}-\d{2}-\d{2})", ln)
                if m:
                    try:
                        meeting_date = date.fromisoformat(m.group(1))
                        if meeting_date >= today:
                            meeting_ok = True
                    except ValueError:
                        pass
                continue
            codes.add(ln)
    return codes if meeting_ok else set()


def load_horse_state(profiles_csv):
    """Return {horse_no: {status, last_race_date, profile_last_scraped}}."""
    if not os.path.exists(profiles_csv):
        return {}
    df = pd.read_csv(profiles_csv, encoding="utf-8-sig")
    state = {}
    for _, row in df.iterrows():
        def _g(col):
            v = row.get(col, "")
            return "" if pd.isna(v) else str(v)
        state[str(row["horse_no"])] = {
            "status": _g("status"),
            "last_race_date": _g("last_race_date"),
            "profile_last_scraped": _g("profile_last_scraped"),
        }
    return state
