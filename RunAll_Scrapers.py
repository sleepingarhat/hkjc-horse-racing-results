"""
Master runner — runs HKJC scrapers grouped into two pools.

Pool A (horse-heavy, sequential — they share the horses/ workspace):
  1. HorseData_Scraper.py       — 馬匹 Profile + 血統 + 往績紀錄
  2. HorseTrackwork_Scraper.py  — 晨操資料
  3. HorseInjury_Scraper.py     — 傷患紀錄

Pool B (light, sequential — fully independent of Pool A):
  1. TrialResults_Scraper.py    — 試閘結果
  2. EntryList_Scraper.py       — 排位表
  3. JockeyData_Scraper.py      — 騎師 Profile + 往績
  4. TrainerData_Scraper.py     — 練馬師 Profile + 往績

Pools are launched in parallel by `run_all_scrapers.sh` so Pool B finishes
fast (~20 min) while Pool A keeps grinding through ~3000 horses (~25h).
"""

import argparse, subprocess, sys, time

from git_sync import push_data_safely

POOLS = {
    "A": [
        ("馬匹 Profile + 血統 + 往績", "HorseData_Scraper.py"),
        ("晨操資料", "HorseTrackwork_Scraper.py"),
        ("傷患紀錄", "HorseInjury_Scraper.py"),
    ],
    "B": [
        ("試閘結果", "TrialResults_Scraper.py"),
        ("排位表 (Entry List)", "EntryList_Scraper.py"),
        ("騎師 Profile + 往績", "JockeyData_Scraper.py"),
        ("練馬師 Profile + 往績", "TrainerData_Scraper.py"),
    ],
}

parser = argparse.ArgumentParser()
parser.add_argument(
    "--pool",
    choices=["A", "B", "ALL"],
    default="ALL",
    help="Which pool to run. ALL = sequential (legacy mode).",
)
parser.add_argument(
    "--no-push",
    action="store_true",
    help="Skip auto-pushing data to GitHub at end of run.",
)
args = parser.parse_args()

if args.pool == "ALL":
    sequence = POOLS["A"] + POOLS["B"]
    pool_label = "ALL (legacy sequential)"
else:
    sequence = POOLS[args.pool]
    pool_label = f"Pool {args.pool}"

print(f"\n[RUNALL] Starting {pool_label} — {len(sequence)} scraper(s)\n")

for label, script in sequence:
    print(f"\n{'=' * 60}")
    print(f"  [{pool_label}] 開始: {label}")
    print(f"  Script: {script}")
    print(f"{'=' * 60}\n")
    start = time.time()
    result = subprocess.run([sys.executable, script])
    elapsed = time.time() - start
    status = "完成" if result.returncode == 0 else f"失敗 (code {result.returncode})"
    print(f"\n  [{pool_label}][{status}] {label} — {elapsed:.0f}秒\n")

print(f"\n[RUNALL] {pool_label} 全部完成。")

if args.no_push:
    print("\n[DATA-SYNC] --no-push set; skipping GitHub push.")
else:
    print("\n[DATA-SYNC] Pushing accumulated data to GitHub...")
    try:
        push_data_safely()
    except Exception as e:
        print(f"[DATA-SYNC] Unexpected error during push: {e}")
