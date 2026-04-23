"""
Race day scraper orchestrator — backfills LocalResults.aspx for a given date.

Writes 5 CSV files per race day (year-partitioned, Replit-compatible):
    data/YYYY/results_YYYY-MM-DD.csv
    data/YYYY/sectional_times_YYYY-MM-DD.csv
    data/YYYY/commentary_YYYY-MM-DD.csv
    data/YYYY/dividends_YYYY-MM-DD.csv
    data/YYYY/video_links_YYYY-MM-DD.csv

Each file contains rows for ALL races on that date (up to 11 races × ~12 horses).
Commentary and results tables are joined on (race_no, horse_no) to fill jockey
and gear in the commentary CSV (HKJC commentary table only has place/horse/event).

Usage:
    python -m scrapers_v2.orchestrator.daily.scrape_race_day \\
        --date 2026-04-22 --venue HV --races 1-9
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from pathlib import Path
from typing import Any

from ...http_client.base import AsyncHKJCClient
from ...parsers.race_results import (
    COMMENTARY_COLS,
    DIVIDEND_COLS,
    RESULT_COLS,
    SECTIONAL_COLS,
    VIDEO_COLS,
    parse_race_results,
)
from ...shared.paths import DATA_DIR

log = logging.getLogger("scrape_race_day")

RESULTS_URL_TEMPLATE = (
    "https://racing.hkjc.com/racing/information/Chinese/racing/LocalResults.aspx"
    "?RaceDate={date_slash}&Racecourse={venue}&RaceNo={race_no}"
)

VENUE_ZH_TO_CODE: dict[str, str] = {"ST": "沙田", "HV": "跑馬地"}


def _parse_range(spec: str) -> list[int]:
    spec = spec.strip()
    if "-" in spec and "," not in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",") if x.strip()]


async def _scrape_one_race(
    client: AsyncHKJCClient,
    date_iso: str,
    venue_code: str,
    venue_zh: str,
    race_no: int,
):
    date_slash = date_iso.replace("-", "/")
    url = RESULTS_URL_TEMPLATE.format(
        date_slash=date_slash, venue=venue_code, race_no=race_no
    )
    try:
        resp = await client.get(url)
    except Exception as e:
        log.warning("GET failed race=%s: %s", race_no, e)
        return None
    if resp.status_code != 200 or len(resp.text) < 1000:
        log.warning("Bad response race=%s status=%s len=%d",
                    race_no, resp.status_code, len(resp.text))
        return None
    try:
        return parse_race_results(
            resp.text, race_date_iso=date_iso, venue_zh=venue_zh, race_no=race_no
        )
    except ValueError as e:
        log.warning("Parse failed race=%s: %s", race_no, e)
        return None


def _enrich_commentary(
    commentary: list[dict[str, Any]], results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Join jockey and gear from results into commentary rows by (race_no, horse_no)."""
    lookup = {(r["race_no"], r["horse_no"]): r for r in results}
    for c in commentary:
        r = lookup.get((c["race_no"], c["horse_no"]))
        if r:
            c["jockey"] = r["jockey"]
            # `gear` not in results table — HKJC only exposes it on racecard/form_records
            # Leave empty; backfill later via horse form join if needed.
    return commentary


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


async def run(
    date_iso: str,
    venue_code: str,
    races: list[int],
    *,
    rate: float = 0.5,
) -> int:
    venue_zh = VENUE_ZH_TO_CODE[venue_code]
    year = date_iso[:4]
    out_dir = DATA_DIR / year

    async with AsyncHKJCClient(rate=rate) as client:
        parsed_list = await asyncio.gather(
            *[_scrape_one_race(client, date_iso, venue_code, venue_zh, n) for n in races]
        )

    results: list[dict] = []
    sectionals: list[dict] = []
    commentary: list[dict] = []
    dividends: list[dict] = []
    videos: list[dict] = []

    for p in parsed_list:
        if p is None:
            continue
        results.extend(p.results)
        sectionals.extend(p.sectional_times)
        commentary.extend(p.commentary)
        dividends.extend(p.dividends)
        videos.extend(p.video_links)

    commentary = _enrich_commentary(commentary, results)

    if not results:
        log.error("No race results scraped for %s (venue=%s)", date_iso, venue_code)
        return 2

    _write_csv(out_dir / f"results_{date_iso}.csv", RESULT_COLS, results)
    _write_csv(out_dir / f"sectional_times_{date_iso}.csv", SECTIONAL_COLS, sectionals)
    _write_csv(out_dir / f"commentary_{date_iso}.csv", COMMENTARY_COLS, commentary)
    _write_csv(out_dir / f"dividends_{date_iso}.csv", DIVIDEND_COLS, dividends)
    _write_csv(out_dir / f"video_links_{date_iso}.csv", VIDEO_COLS, videos)

    log.info(
        "Race day %s (%s): %d races, %d horses, %d dividend rows → %s",
        date_iso, venue_code,
        sum(1 for p in parsed_list if p is not None),
        len(results), len(dividends), out_dir,
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    p.add_argument("--venue", required=True, choices=["ST", "HV"])
    p.add_argument("--races", default="1-11")
    p.add_argument("--rate", type=float, default=0.5)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    races = _parse_range(args.races)
    return asyncio.run(run(args.date, args.venue, races, rate=args.rate))


if __name__ == "__main__":
    raise SystemExit(main())
