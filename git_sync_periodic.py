"""
Periodic background pusher — wakes every PUSH_INTERVAL_SEC and runs
push_data_safely() so accumulated scraping data is backed up to GitHub
incrementally instead of only at end of RunAll.

Runs as background sidecar from run_all_scrapers.sh.
Never crashes the parent (catches all exceptions, just logs and continues).
"""
import os
import time
import traceback
from datetime import datetime, timezone

from git_sync import push_data_safely

PUSH_INTERVAL_SEC = int(os.environ.get("PUSH_INTERVAL_SEC", "1800"))  # 30 min default
INITIAL_DELAY_SEC = int(os.environ.get("PUSH_INITIAL_DELAY_SEC", "600"))  # 10 min warm-up


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    print(f"[periodic-sync] {_ts()} starting; interval={PUSH_INTERVAL_SEC}s, "
          f"initial_delay={INITIAL_DELAY_SEC}s", flush=True)
    time.sleep(INITIAL_DELAY_SEC)
    while True:
        try:
            print(f"[periodic-sync] {_ts()} attempting push...", flush=True)
            ok = push_data_safely(message_override=f"periodic backup {_ts()}")
            print(f"[periodic-sync] {_ts()} push result={ok}", flush=True)
        except Exception as e:
            print(f"[periodic-sync] {_ts()} unexpected error: {e}", flush=True)
            traceback.print_exc()
        time.sleep(PUSH_INTERVAL_SEC)


if __name__ == "__main__":
    main()
