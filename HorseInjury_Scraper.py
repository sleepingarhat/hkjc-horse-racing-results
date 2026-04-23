"""
Horse Injury / Veterinary Records Scraper.

Source page (per horse):
  https://racing.hkjc.com/zh-hk/local/information/ovehorse?horseid=HK_YYYY_BRAND

Each horse page contains a small table with columns:
    日期 | 詳情 | 通過日期
representing each veterinary / injury / movement event.

Output:
  horses/injury/injury_<brand_no>.csv  (one row per event; written only if
                                        the horse has at least one record)
  horses/injury/_horseid_map.json      (cache of brand_no -> HK_YYYY_BRAND)

Strategy:
  1. For each brand_no in horse_profiles.csv (or fallback: scan horse pages),
     resolve its `horseid` (HK_YYYY_BRAND) — cached in _horseid_map.json.
  2. Fetch ovehorse page, regex-parse the injury table.
  3. Persist as CSV (overwrite each run; small data volume).

Pure stdlib + requests (no Selenium needed — page is server-rendered).
"""
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

PROFILES_CSV = os.path.join("horses", "profiles", "horse_profiles.csv")
INJURY_DIR = os.path.join("horses", "injury")
HORSEID_MAP = os.path.join(INJURY_DIR, "_horseid_map.json")
FAILED_LOG = "failed_injury.log"

OLD_PROFILE_URL = "https://racing.hkjc.com/racing/information/Chinese/Horse/Horse.aspx?HorseNo={brand}"
OVEHORSE_URL = "https://racing.hkjc.com/zh-hk/local/information/ovehorse?horseid={hid}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
}

REQUEST_TIMEOUT = 30
RETRIES = 3
SLEEP_BETWEEN = 0.4  # be nice to HKJC

os.makedirs(INJURY_DIR, exist_ok=True)


def _log(msg: str) -> None:
    print(f"[injury] {msg}", flush=True)


def _log_failed(brand: str, reason: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(FAILED_LOG, "a") as f:
        f.write(f"{brand}  # {reason}  [{ts}]\n")


def _fetch(url: str) -> str | None:
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if r.status_code == 200 and r.text:
                return r.text
            last_err = f"status={r.status_code}"
        except requests.RequestException as e:
            last_err = str(e)
        time.sleep(2 * attempt)
    _log(f"  fetch failed after {RETRIES} attempts: {url} ({last_err})")
    return None


def _load_horseid_map() -> dict:
    if os.path.isfile(HORSEID_MAP):
        try:
            with open(HORSEID_MAP, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_horseid_map(m: dict) -> None:
    with open(HORSEID_MAP, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2, ensure_ascii=False)


def resolve_horseid(brand: str, cache: dict) -> str | None:
    """Return HK_YYYY_BRAND for a brand_no like 'L108'.

    Strict-match only: the captured horseid MUST end with `_<brand>` to avoid
    cache poisoning by unrelated horses linked from the same page.
    """
    if brand in cache:
        return cache[brand]
    html = _fetch(OLD_PROFILE_URL.format(brand=brand))
    if not html:
        return None
    m = re.search(rf"horseid=(HK_\d{{4}}_{re.escape(brand)})\b", html)
    if m:
        cache[brand] = m.group(1)
        return m.group(1)
    return None


def _invalidate_cache(brand: str, cache: dict) -> None:
    """Drop a stale horseid so it re-resolves on next attempt."""
    cache.pop(brand, None)


# Recognise the injury table by its 3-column header row.
HEADER_PAT = re.compile(
    r"<tr[^>]*>\s*<t[hd][^>]*>\s*日期\s*</t[hd]>\s*"
    r"<t[hd][^>]*>\s*詳情\s*</t[hd]>\s*"
    r"<t[hd][^>]*>\s*通過日期\s*</t[hd]>\s*</tr>",
    re.S,
)
TABLE_PAT = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
ROW_PAT = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL_PAT = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
TAG_PAT = re.compile(r"<[^>]+>")
WS_PAT = re.compile(r"\s+")


def _clean(s: str) -> str:
    s = TAG_PAT.sub(" ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    s = WS_PAT.sub(" ", s).strip()
    return s


def parse_injury_records(html: str) -> list[dict]:
    """Extract list of {date, detail, cleared_date} from ovehorse HTML.

    Preserves positional cells: 通過日期 is often blank for ongoing cases —
    we must keep that empty third column instead of dropping it.
    """
    for table_html in TABLE_PAT.findall(html):
        if not HEADER_PAT.search(table_html):
            continue
        rows = []
        for row_html in ROW_PAT.findall(table_html):
            cells = [_clean(c) for c in CELL_PAT.findall(row_html)]
            if len(cells) < 3:
                continue
            if cells[0] == "日期":  # skip header
                continue
            if not cells[0] and not cells[1]:  # truly empty row
                continue
            rows.append({
                "date": cells[0],
                "detail": cells[1],
                "cleared_date": cells[2],
            })
        return rows
    return []


def write_injury_csv(brand: str, records: list[dict]) -> None:
    path = os.path.join(INJURY_DIR, f"injury_{brand}.csv")
    if not records:
        # remove stale file if horse no longer has records
        if os.path.exists(path):
            os.remove(path)
        return
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["horse_no", "date", "detail", "cleared_date"])
        w.writeheader()
        for r in records:
            w.writerow({"horse_no": brand, **r})


def collect_brand_nos() -> list[str]:
    """Pull brand_no list from horse_profiles.csv (preferred) or by scanning
    form_records/ filenames as fallback."""
    brands: list[str] = []
    if os.path.isfile(PROFILES_CSV):
        try:
            import pandas as pd
            df = pd.read_csv(PROFILES_CSV, encoding="utf-8-sig")
            for col in ["horse_no", "brand_no", "code"]:
                if col in df.columns:
                    brands = sorted({str(x).strip() for x in df[col].dropna() if str(x).strip()})
                    break
        except Exception as e:
            _log(f"  could not read {PROFILES_CSV}: {e}")
    if not brands:
        form_dir = os.path.join("horses", "form_records")
        if os.path.isdir(form_dir):
            brands = sorted({
                fn.replace("form_", "").replace(".csv", "")
                for fn in os.listdir(form_dir)
                if fn.startswith("form_") and fn.endswith(".csv")
            })
    return brands


def main() -> int:
    brands = collect_brand_nos()
    if not brands:
        _log("No horses found (need horse_profiles.csv or form_records/).")
        return 0

    _log(f"Scraping injury records for {len(brands)} horses...")
    cache = _load_horseid_map()
    saved = 0
    no_record = 0
    failed = 0

    for i, brand in enumerate(brands, 1):
        try:
            hid = resolve_horseid(brand, cache)
            if not hid:
                _log_failed(brand, "no horseid")
                failed += 1
                continue
            html = _fetch(OVEHORSE_URL.format(hid=hid))
            if not html:
                # Cache may be stale (horse re-registered with new HK_YYYY).
                # Drop and retry once with a fresh resolve.
                _invalidate_cache(brand, cache)
                hid_retry = resolve_horseid(brand, cache)
                if hid_retry and hid_retry != hid:
                    html = _fetch(OVEHORSE_URL.format(hid=hid_retry))
                if not html:
                    _log_failed(brand, "ovehorse fetch failed")
                    failed += 1
                    continue
            records = parse_injury_records(html)
            write_injury_csv(brand, records)
            if records:
                saved += 1
            else:
                no_record += 1
            if i % 50 == 0:
                _log(f"  [{i}/{len(brands)}] saved={saved} empty={no_record} failed={failed}")
                _save_horseid_map(cache)
        except Exception as e:
            _log_failed(brand, f"unexpected: {e}")
            failed += 1
        time.sleep(SLEEP_BETWEEN)

    _save_horseid_map(cache)
    _log(f"Done. saved={saved} empty={no_record} failed={failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
