"""
Tianxi — Comeback Detection for HKJC Scrapers
Pure logic, no DB dependency. CSV-based state is passed in via parameters.
Unit tested separately (8 cases: comeback, quarterly safety net, inactive
monthly rescan, first_time, edge cases).
"""
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from typing import Optional, Set
import logging

logger = logging.getLogger("tianxi.comeback")

INACTIVE_THRESHOLD_MONTHS = 6
RETIRED_THRESHOLD_MONTHS = 24
INACTIVE_RESCAN_DAYS = 30
RETIRED_RESCAN_DAYS = 90


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _months_ago(m, today=None):
    return (today or date.today()) - timedelta(days=m * 30)


def _days_ago(d, today=None):
    return (today or date.today()) - timedelta(days=d)


def classify_status(last_race_date, today=None):
    last = _parse_date(last_race_date)
    if last is None:
        return "retired"
    today = today or date.today()
    if last >= _months_ago(INACTIVE_THRESHOLD_MONTHS, today):
        return "active"
    if last >= _months_ago(RETIRED_THRESHOLD_MONTHS, today):
        return "inactive"
    return "retired"


@dataclass
class HorseScrapeDecision:
    horse_id: str
    should_scrape: bool
    reason: str
    new_status: Optional[str] = None


def should_scrape(horse_id,
                  today_entries: Optional[Set[str]] = None,
                  *,
                  current_status: Optional[str] = None,
                  last_race_date: Optional[str] = None,
                  profile_last_scraped: Optional[str] = None,
                  today: Optional[date] = None) -> HorseScrapeDecision:
    """
    Decide whether to (re)scrape a horse.

    today_entries: set of horse codes appearing in today's HKJC entry list.
                   None or empty => no entry-list signal available;
                   walks the inactive/retired rescan path (no comeback override).
    """
    today = today or date.today()
    expected = classify_status(last_race_date, today)
    in_entry = bool(today_entries) and (horse_id in today_entries)

    # Rule 1: COMEBACK — retired/inactive but appears in today's entry list
    if in_entry and expected in ("inactive", "retired"):
        logger.warning(
            "COMEBACK: horse=%s last_race=%s status=%s -> force refresh",
            horse_id, last_race_date, expected,
        )
        return HorseScrapeDecision(horse_id, True, f"comeback_from_{expected}", "comeback")

    # Rule 2: in today's entry list -> active
    if in_entry:
        return HorseScrapeDecision(horse_id, True, "active_entry", "active")

    # Rule 3: never scraped before
    if not profile_last_scraped:
        return HorseScrapeDecision(horse_id, True, "first_time", expected)

    last_scrape = _parse_date(profile_last_scraped)

    # Rule 4: active -> always scrape
    if expected == "active":
        return HorseScrapeDecision(horse_id, True, "status_active", "active")

    # Rule 5: inactive -> monthly rescan
    if expected == "inactive":
        if last_scrape is None or last_scrape < _days_ago(INACTIVE_RESCAN_DAYS, today):
            return HorseScrapeDecision(horse_id, True, "inactive_monthly_rescan", "inactive")
        return HorseScrapeDecision(horse_id, False, "inactive_recently_scraped", "inactive")

    # Rule 6: retired -> quarterly safety net
    if expected == "retired":
        if last_scrape is None or last_scrape < _days_ago(RETIRED_RESCAN_DAYS, today):
            logger.info(
                "[LIFECYCLE] Quarterly rescan: %s (retired since %s)",
                horse_id, last_race_date,
            )
            return HorseScrapeDecision(horse_id, True, "retired_quarterly_rescan", "retired")
        return HorseScrapeDecision(horse_id, False, "retired_recently_scraped", "retired")

    return HorseScrapeDecision(horse_id, True, "unknown_fallback", expected)
