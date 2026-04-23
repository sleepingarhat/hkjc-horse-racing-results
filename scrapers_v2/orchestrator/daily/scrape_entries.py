"""
Entries (Racecard) scraper orchestrator — replaces Replit's EntryList SPA polling.

Usage:
    python -m scrapers_v2.orchestrator.daily.scrape_entries \\
        --date 2026-04-26 --venue ST --races 1-10

Writes:
    entries/entries_YYYY-MM-DD.txt           (horse_no list per meeting)
    entries/races/YYYY-MM-DD_<venue>_r<n>.csv (per-race full entry CSV)
    entries/races/YYYY-MM-DD_<venue>_r<n>_meta.csv (one-row race meta)

The .txt is kept for byte-parity with Replit `entries/entries_YYYY-MM-DD.txt`.
The per-race CSV is new (Capy-only) — Replit never stored structured racecard data.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from pathlib import Path

from ...http_client.base import AsyncHKJCClient
from ...parsers.entries import ENTRY_COLS, RACE_META_COLS, parse_racecard
from ...shared.paths import ENTRIES_DIR

log = logging.getLogger("scrape_entries")

RACECARD_URL_TEMPLATE = (
    "https://racing.hkjc.com/racing/information/chinese/Racing/RaceCard.aspx"
    "?RaceDate={date_slash}&Racecourse={venue}&RaceNo={race_no}"
)

ENTRIES_RACES_DIR = ENTRIES_DIR / "races"


def _parse_range(spec: str) -> list[int]:
    """'1-10' → [1..10], '1,3,5' → [1,3,5]."""
    spec = spec.strip()
    if "-" in spec and "," not in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",") if x.strip()]


async def _scrape_one_race(
    client: AsyncHKJCClient, date_iso: str, venue: str, race_no: int
) -> tuple[dict, list[dict]] | None:
    date_slash = date_iso.replace("-", "/")
    url = RACECARD_URL_TEMPLATE.format(date_slash=date_slash, venue=venue, race_no=race_no)
    try:
        resp = await client.get(url)
    except Exception as e:
        log.warning("GET failed race=%s %s: %s", race_no, url, e)
        return None
    if resp.status_code != 200 or len(resp.text) < 1000:
        log.warning("Unexpected response race=%s status=%s len=%d",
                    race_no, resp.status_code, len(resp.text))
        return None
    parsed = parse_racecard(resp.text, source_url=url)
    if not parsed.entries:
        log.warning("No entries parsed for race=%s", race_no)
        return None
    return parsed.meta, parsed.entries


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def _write_entries_txt(path: Path, horse_nos: list[str], date_iso: str, venue: str) -> None:
    """Replit-compatible plain text list."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# meeting={date_iso} racecourse={venue} written={date_iso}\n")
        for hno in horse_nos:
            f.write(f"{hno}\n")


async def run(date_iso: str, venue: str, races: list[int], *, rate: float = 0.8) -> int:
    ENTRIES_RACES_DIR.mkdir(parents=True, exist_ok=True)

    async with AsyncHKJCClient(rate=rate) as client:
        tasks = [_scrape_one_race(client, date_iso, venue, n) for n in races]
        results = await asyncio.gather(*tasks)

    all_horse_nos: list[str] = []
    successful_races = 0
    for race_no, result in zip(races, results):
        if result is None:
            continue
        meta, entries = result
        meta_path = ENTRIES_RACES_DIR / f"{date_iso}_{venue}_r{race_no}_meta.csv"
        entries_path = ENTRIES_RACES_DIR / f"{date_iso}_{venue}_r{race_no}.csv"
        _write_csv(meta_path, RACE_META_COLS, [meta])
        _write_csv(entries_path, ENTRY_COLS, entries)
        for e in entries:
            if e.get("is_reserve"):
                continue
            hno = e.get("horse_no")
            if hno and hno not in all_horse_nos:
                all_horse_nos.append(str(hno))
        successful_races += 1

    # Legacy Replit .txt format (but write deduped brand codes derived from entries)
    # NOTE: Replit's .txt has brand codes (e.g. H066) not race-position numbers.
    # Our parser stores `horse_no` as race position (1-14). True brand codes are in `brand_no`.
    brand_codes: list[str] = []
    for race_no, result in zip(races, results):
        if result is None:
            continue
        _meta, entries = result
        for e in entries:
            if e.get("is_reserve"):
                continue
            brand = e.get("brand_no")
            if brand and brand not in brand_codes:
                brand_codes.append(str(brand))
    txt_path = ENTRIES_DIR / f"entries_{date_iso}.txt"
    _write_entries_txt(txt_path, brand_codes, date_iso, venue)

    log.info("Scraped %d/%d races, %d unique horses → %s",
             successful_races, len(races), len(brand_codes), ENTRIES_DIR)
    return 0 if successful_races > 0 else 2


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True, help="ISO date e.g. 2026-04-26")
    p.add_argument("--venue", required=True, choices=["ST", "HV"])
    p.add_argument("--races", default="1-11",
                   help="Range '1-11' or list '1,3,5' (default 1-11)")
    p.add_argument("--rate", type=float, default=0.8,
                   help="Max req/s (default 0.8)")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    races = _parse_range(args.races)
    return asyncio.run(run(args.date, args.venue, races, rate=args.rate))


if __name__ == "__main__":
    raise SystemExit(main())
