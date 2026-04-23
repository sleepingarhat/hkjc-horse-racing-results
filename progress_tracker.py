"""
HKJC Scraper Progress Tracker
Displays real-time status of all scraped data categories.
"""

import os, time, glob

OUTPUT_DIR  = "data"
HORSES_DIR  = "horses"
JOCKEYS_DIR = "jockeys"
TRAINER_DIR = "trainers"
TRIALS_DIR  = "trials"

WIDTH = 62

def count_files(pattern):
    return len(glob.glob(pattern))

def count_csv_rows(filepath):
    try:
        with open(filepath, encoding="utf-8-sig") as f:
            return max(0, sum(1 for _ in f) - 1)
    except Exception:
        return 0

def log_count(logfile):
    try:
        with open(logfile) as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0

while True:
    os.system("clear")
    print("=" * WIDTH)
    print("      HKJC 全數據擷取系統 — 進度報告")
    print("=" * WIDTH)

    # ── 賽事資料 ────────────────────────────────────────────
    print("\n  【賽事資料】（每個賽馬日）")
    print(f"  {'年份':<8} {'賽果':<6} {'分段':<6} {'評述':<6} {'派彩':<6} {'錄像':<6}")
    total_results  = 0
    total_sect     = 0
    total_comm     = 0
    total_divs     = 0
    total_vids     = 0
    for year in range(2016, 2027):
        ydir = os.path.join(OUTPUT_DIR, str(year))
        if not os.path.isdir(ydir):
            continue
        nr = count_files(os.path.join(ydir, "results_*.csv"))
        ns = count_files(os.path.join(ydir, "sectional_times_*.csv"))
        nc = count_files(os.path.join(ydir, "commentary_*.csv"))
        nd = count_files(os.path.join(ydir, "dividends_*.csv"))
        nv = count_files(os.path.join(ydir, "video_links_*.csv"))
        total_results += nr; total_sect += ns
        total_comm += nc; total_divs += nd; total_vids += nv
        if nr or ns or nc:
            print(f"  {year:<8} {nr:<6} {ns:<6} {nc:<6} {nd:<6} {nv:<6}")
    print(f"  {'合計':<8} {total_results:<6} {total_sect:<6} {total_comm:<6} {total_divs:<6} {total_vids:<6}")

    # ── 馬匹資料 ────────────────────────────────────────────
    print("\n  【馬匹資料】")
    hp = os.path.join(HORSES_DIR, "profiles", "horse_profiles.csv")
    n_profiles   = count_csv_rows(hp) if os.path.exists(hp) else 0
    n_form       = count_files(os.path.join(HORSES_DIR, "form_records", "form_*.csv"))
    n_trackwork  = count_files(os.path.join(HORSES_DIR, "trackwork", "trackwork_*.csv"))
    print(f"  馬匹Profile(含血統):        {n_profiles:>6} 匹")
    print(f"  往績紀錄檔:                   {n_form:>6} 匹")
    print(f"  晨操紀錄檔:                   {n_trackwork:>6} 匹")

    # ── 騎師資料 ────────────────────────────────────────────
    print("\n  【騎師資料】")
    jp = os.path.join(JOCKEYS_DIR, "jockey_profiles.csv")
    n_jprofiles = count_csv_rows(jp) if os.path.exists(jp) else 0
    n_jrec      = count_files(os.path.join(JOCKEYS_DIR, "records", "jockey_*.csv"))
    print(f"  騎師Profile:                  {n_jprofiles:>6} 名")
    print(f"  往績紀錄檔:                   {n_jrec:>6} 名")

    # ── 練馬師資料 ──────────────────────────────────────────
    print("\n  【練馬師資料】")
    tp = os.path.join(TRAINER_DIR, "trainer_profiles.csv")
    n_tprofiles = count_csv_rows(tp) if os.path.exists(tp) else 0
    n_trec      = count_files(os.path.join(TRAINER_DIR, "records", "trainer_*.csv"))
    print(f"  練馬師Profile:                {n_tprofiles:>6} 名")
    print(f"  往績紀錄檔:                   {n_trec:>6} 名")

    # ── 試閘結果 ────────────────────────────────────────────
    print("\n  【試閘結果】")
    tr = os.path.join(TRIALS_DIR, "trial_results.csv")
    ts = os.path.join(TRIALS_DIR, "trial_sessions.csv")
    n_trial_horses   = count_csv_rows(tr) if os.path.exists(tr) else 0
    n_trial_sessions = count_csv_rows(ts) if os.path.exists(ts) else 0
    print(f"  試閘馬次(合計):             {n_trial_horses:>6} 次")
    print(f"  試閘組別(合計):             {n_trial_sessions:>6} 組")

    # ── 失敗紀錄 ────────────────────────────────────────────
    print("\n  【失敗/略過紀錄】")
    any_fail = False
    for log in ["failed_dates.log", "failed_horses.log", "failed_trackwork.log",
                "failed_jockeys.log", "failed_trainers.log", "failed_trials.log"]:
        n = log_count(log)
        if n:
            print(f"  {log:<32} {n:>4} 項")
            any_fail = True
    if not any_fail:
        print("  (暫無失敗項目)")

    # ── 不可公開存取之資料 ───────────────────────────────────
    print("\n  【HKJC 未公開/已下架頁面(無法擷取)】")
    print("  排位表(歷史)、天氣跑道狀況(歷史)、速勢能量、")
    print("  馬匹搬遷紀錄、裝備登記冊、傷患紀錄、上仗備忘")

    print(f"\n  更新時間: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * WIDTH)
    time.sleep(30)
