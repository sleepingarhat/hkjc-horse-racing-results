"""
Pool A orchestrator — horse profile + form records in one pass.

Replit note: single URL Horse.aspx?HorseNo=XXX serves BOTH profile and
form records (same page). We fetch once, parse both.

Universe: 5,827 horses (derived from data/YYYY/results_*.csv history),
minus PHANTOM_HORSE_NOS (Replit confirmed-dead skiplist).

Writes:
  horses/profiles/horse_profiles.csv       (one row per horse, 16 cols)
  horses/form_records/form_<HORSE_NO>.csv  (N rows per horse, 21 cols)

Idempotency: per-horse form CSVs use file-exists check for skip-if-done mode.

Usage:
    python -m scrapers_v2.orchestrator.pool_a.scrape_horses \\
        --limit 10                 # smoke test
    python -m scrapers_v2.orchestrator.pool_a.scrape_horses \\
        --skip-existing            # skip horses with existing form CSV
    python -m scrapers_v2.orchestrator.pool_a.scrape_horses \\
        --horses A001,K056         # specific horse_no list
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from pathlib import Path

from ...http_client.base import AsyncHKJCClient
from ...parsers.horse_form import FORM_COLS, parse_form_records
from ...parsers.horse_profile import PROFILE_COLS, parse_profile
from ...shared.paths import DATA_DIR, HORSE_FORM_DIR, HORSE_PROFILES_DIR
from ...shared.skiplist import is_phantom

log = logging.getLogger("scrape_horses")

HORSE_URL = "https://racing.hkjc.com/racing/information/chinese/Horse/Horse.aspx?HorseNo={hno}"


def _derive_universe() -> list[str]:
    """Extract unique horse_no (brand codes) from all results CSVs in data/."""
    import re

    horses: set[str] = set()
    brand_re = re.compile(r"\(([A-Z0-9]+)\)")
    for year_dir in sorted(DATA_DIR.iterdir()):
        if not year_dir.is_dir():
            continue
        for csv_path in year_dir.glob("results_*.csv"):
            try:
                with csv_path.open(encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name = row.get("horse_name") or ""
                        m = brand_re.search(name)
                        if m:
                            horses.add(m.group(1).upper())
            except Exception as e:
                log.warning("Failed to read %s: %s", csv_path, e)
    return sorted(horses)


async def _scrape_one_horse(
    client: AsyncHKJCClient, horse_no: str
) -> tuple[dict | None, list[dict]]:
    url = HORSE_URL.format(hno=horse_no)
    try:
        resp = await client.get(url)
    except Exception as e:
        log.warning("GET failed %s: %s", horse_no, e)
        return None, []
    if resp.status_code != 200 or len(resp.text) < 1000:
        log.warning("Bad response %s status=%s len=%d", horse_no, resp.status_code, len(resp.text))
        return None, []
    profile = parse_profile(resp.text, horse_no)
    form = parse_form_records(resp.text, horse_no)
    return profile, form


def _write_form_csv(horse_no: str, rows: list[dict]) -> None:
    path = HORSE_FORM_DIR / f"form_{horse_no}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FORM_COLS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FORM_COLS})


def _append_profile(profiles: list[dict]) -> None:
    """Atomic write of the full profiles CSV — dedupe by horse_no, keep last."""
    path = HORSE_PROFILES_DIR / "horse_profiles.csv"
    path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing
    existing: dict[str, dict] = {}
    if path.exists():
        with path.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                hno = (row.get("horse_no") or "").upper().strip()
                if hno:
                    existing[hno] = row

    # Overlay new
    for p in profiles:
        hno = str(p.get("horse_no") or "").upper().strip()
        if hno:
            existing[hno] = p

    # Write deduped
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PROFILE_COLS)
        writer.writeheader()
        for hno in sorted(existing.keys()):
            row = existing[hno]
            writer.writerow({k: row.get(k, "") for k in PROFILE_COLS})


async def run(
    horses: list[str] | None,
    *,
    limit: int | None,
    skip_existing: bool,
    rate: float,
) -> int:
    if horses is None:
        universe = _derive_universe()
    else:
        universe = [h.strip().upper() for h in horses if h.strip()]

    # Apply phantom skip
    universe = [h for h in universe if not is_phantom(h)]

    # Apply skip-existing
    if skip_existing:
        before = len(universe)
        universe = [
            h for h in universe
            if not (HORSE_FORM_DIR / f"form_{h}.csv").exists()
        ]
        log.info("Skip-existing: %d → %d horses remaining", before, len(universe))

    if limit is not None:
        universe = universe[:limit]

    log.info("Scraping %d horses at %s req/s", len(universe), rate)

    profiles: list[dict] = []
    form_success = 0

    async with AsyncHKJCClient(rate=rate) as client:
        # Chunk to avoid memory blow-up with 5827 horses
        chunk_size = 50
        for i in range(0, len(universe), chunk_size):
            chunk = universe[i:i + chunk_size]
            results = await asyncio.gather(
                *[_scrape_one_horse(client, h) for h in chunk]
            )
            for hno, (profile, form) in zip(chunk, results):
                if profile:
                    profiles.append(profile)
                if form:
                    _write_form_csv(hno, form)
                    form_success += 1
            log.info("Chunk %d/%d done", i // chunk_size + 1, (len(universe) + chunk_size - 1) // chunk_size)

    _append_profile(profiles)

    log.info(
        "Pool A done: %d profiles, %d form CSVs written (out of %d horses)",
        len(profiles), form_success, len(universe),
    )
    return 0 if profiles else 2


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--horses", default=None, help="Comma-separated brand codes (e.g. A001,K056)")
    p.add_argument("--limit", type=int, default=None, help="Smoke-test limit")
    p.add_argument("--skip-existing", action="store_true", help="Skip horses with form CSV")
    p.add_argument("--rate", type=float, default=0.5)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    horses = args.horses.split(",") if args.horses else None
    return asyncio.run(run(horses, limit=args.limit, skip_existing=args.skip_existing, rate=args.rate))


if __name__ == "__main__":
    raise SystemExit(main())
