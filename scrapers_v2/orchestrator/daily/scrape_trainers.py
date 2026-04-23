"""
Trainer scraper orchestrator — fixes the D1 silent-fail bug from Replit's
TrainerData_Scraper.py (trainer-ranking SPA URL broke stats parsing).

P0 objective:
  - Writes trainers/trainer_profiles.csv with 14 PINNED columns (not 2)
  - Writes trainers/records/<TRAINER_ID>.csv with 18 PINNED columns
    (records dir did NOT exist on Replit — this is new data)
  - Dedupes by trainer_id (keep last), fixing the 1431-row dupe bug

Trainer ID source: reads existing trainers/trainer_profiles.csv (67 IDs).
For fresh ID enumeration from trainer-ranking SPA, a separate Playwright
orchestrator (weekly) is needed — see orchestrator/weekly/refresh_trainer_ids.py.

Usage:
    python -m scrapers_v2.orchestrator.daily.scrape_trainers
    python -m scrapers_v2.orchestrator.daily.scrape_trainers --ids FC,MKL,PP
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from pathlib import Path

from ...http_client.base import AsyncHKJCClient
from ...parsers.trainer import (
    TRAINER_PROFILE_COLS,
    TRAINER_RECORD_COLS,
    parse_profile,
    parse_records,
)
from ...shared.paths import TRAINER_RECORDS_DIR, TRAINERS_DIR

log = logging.getLogger("scrape_trainers")

PROFILE_URL = (
    "https://racing.hkjc.com/racing/information/chinese/Trainers/"
    "TrainerProfile.aspx?TrainerId={tid}"
)
RECORDS_URL = (
    "https://racing.hkjc.com/racing/information/chinese/Trainers/"
    "TrainerPastRec.aspx?TrainerId={tid}&Season=Current"
)


def _load_trainer_ids(ids_arg: str | None) -> list[tuple[str, str]]:
    """Return list of (trainer_id, trainer_name). Falls back to existing CSV."""
    if ids_arg:
        return [(tid.strip().upper(), "") for tid in ids_arg.split(",") if tid.strip()]
    existing_csv = TRAINERS_DIR / "trainer_profiles.csv"
    if not existing_csv.exists():
        log.error("No --ids given and %s missing. Cannot bootstrap.", existing_csv)
        return []
    out: list[tuple[str, str]] = []
    with existing_csv.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid = (row.get("trainer_code") or row.get("trainer_id") or "").strip().upper()
            name = (row.get("trainer_name") or "").strip()
            if tid and (tid, name) not in out:
                out.append((tid, name))
    return out


async def _scrape_one_trainer(
    client: AsyncHKJCClient,
    trainer_id: str,
    known_name: str,
    season: str = "25/26",
) -> tuple[dict | None, list[dict]]:
    profile: dict | None = None
    try:
        resp = await client.get(PROFILE_URL.format(tid=trainer_id))
        if resp.status_code == 200 and len(resp.text) > 500:
            profile = parse_profile(resp.text, trainer_id)
    except Exception as e:
        log.warning("Profile GET failed tid=%s: %s", trainer_id, e)

    records: list[dict] = []
    try:
        resp = await client.get(RECORDS_URL.format(tid=trainer_id))
        if resp.status_code == 200 and len(resp.text) > 500:
            name_for_records = (profile or {}).get("trainer_name") or known_name or ""
            records = parse_records(resp.text, trainer_id, name_for_records, season)
    except Exception as e:
        log.warning("Records GET failed tid=%s: %s", trainer_id, e)

    return profile, records


def _write_profiles_csv(rows: list[dict]) -> None:
    path = TRAINERS_DIR / "trainer_profiles.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Deduplicate by trainer_id keeping the LAST occurrence (freshest data)
    seen: dict[str, dict] = {}
    for r in rows:
        tid = str(r.get("trainer_id") or "").upper()
        if tid:
            seen[tid] = r
    deduped = list(seen.values())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRAINER_PROFILE_COLS)
        writer.writeheader()
        for row in deduped:
            writer.writerow({k: row.get(k, "") for k in TRAINER_PROFILE_COLS})


def _write_records_csv(trainer_id: str, rows: list[dict]) -> None:
    if not rows:
        return
    path = TRAINER_RECORDS_DIR / f"{trainer_id}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRAINER_RECORD_COLS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in TRAINER_RECORD_COLS})


async def run(ids_arg: str | None, *, rate: float = 0.25) -> int:
    trainer_ids = _load_trainer_ids(ids_arg)
    if not trainer_ids:
        return 2
    log.info("Scraping %d trainers at %s req/s", len(trainer_ids), rate)

    all_profiles: list[dict] = []
    all_records_by_id: dict[str, list[dict]] = {}

    async with AsyncHKJCClient(rate=rate) as client:
        tasks = [_scrape_one_trainer(client, tid, name) for tid, name in trainer_ids]
        results = await asyncio.gather(*tasks)

    profile_success = 0
    records_success = 0
    for (tid, _name), (profile, records) in zip(trainer_ids, results):
        if profile:
            all_profiles.append(profile)
            profile_success += 1
        if records:
            all_records_by_id[tid] = records
            records_success += 1

    _write_profiles_csv(all_profiles)
    for tid, rows in all_records_by_id.items():
        _write_records_csv(tid, rows)

    log.info(
        "Done. Profiles: %d/%d success. Records: %d/%d success. Profile file deduped to %d unique.",
        profile_success, len(trainer_ids),
        records_success, len(trainer_ids),
        len({str(p.get("trainer_id") or "").upper() for p in all_profiles if p.get("trainer_id")}),
    )
    return 0 if profile_success > 0 else 2


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ids", default=None, help="Comma-separated trainer IDs. Default: load from existing CSV.")
    p.add_argument("--rate", type=float, default=0.25)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    return asyncio.run(run(args.ids, rate=args.rate))


if __name__ == "__main__":
    raise SystemExit(main())
