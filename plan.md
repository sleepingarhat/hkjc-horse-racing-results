# 天喜數據庫 · 實施計劃 & 當前狀態

**最後更新:** 2026-04-24
**版本:** Full GHA cutover + integrity audit
**下一個里程碑:** Audit 7 日連續全綠 → baseline tag `capy-handover-baseline-v1`
**核心原則:** **數據 100% 齊全，唔可以遺漏。**

---

## A · 當前狀態（Backend 邏輯層）

### A1 · Workflow matrix (9 條 auto)

| # | Workflow | Cron (HK) | Fixture Guard | 狀態 | 近 48h |
|---|---|---|---|---|---|
| 1 | `capy_pool_b_daily.yml` | 02:00 | – | auto | 2/2 success |
| 2 | `capy_pool_a.yml` | 04:00 | 昨日有賽 | auto | backfill dispatched |
| 3 | `capy_race_daily.yml` | 賽日 23:30 | 今日有賽 | auto | 1/1 success |
| 4 | `capy_entries.yml` | 20:00 Mon/Tue/Sat | 明日有賽 | auto | 1/1 success |
| 5 | `capy_trainer_fix.yml` | 01:00 | 過去 2 日有賽 | auto | 2/2 success |
| 6 | `capy_fixture_weekly.yml` | 週一 05:00 | – | auto | 2/2 success |
| 7 | `capy_sanity_daily.yml` | 10:03 | – | auto | 1/1 success |
| 8 | `capy_integrity_audit.yml` | 11:00 | – | auto | 1st run baselined |
| 9 | `elo-v11.yml` | 04:00 / on push | – | auto | green |

### A2 · 數據層規模（2026-04-24 實測精準）

| Artefact | 數量 / Size |
|---|---|
| Race days | **886** (2016-2026) |
| 實際 races | **8,361** (distinct date × race_no) |
| Horse-entry rows | **106,004** (每匹馬每場 1 row) |
| Races/day (min-mean-max) | 6 · 9.44 · 11 |
| Horses/race mean | 12.68 |
| 每 race day 5 個 artefact | results · commentary · dividends · sectional_times · video_links |
| Horse profiles | 1,886 (大部分舊 cohort，active backfill in progress) |
| Horse form_records | 1,899 files |
| Trainer profiles | 67 |
| Jockey profiles | 64 |
| Trials | 5,579 rows |
| Fixture dates (2025+2026) | 152 days |
| CSV 總 size | ~90 MB |

### A3 · 已知數據空洞 (2026-04-24 audit)

- **1,268 匹現役馬** (D-L 代 debut) 過去 180 日有落場，但冇 profile
- **1,268 匹 form_records 缺失**
- 10 個 2025-08 race day artefact 殘缺
- 67 個 trainer `records/*.csv` 全部 missing
- 5 個 jockey `records/*.csv` missing
- 1 個 upcoming race day 冇 entries

詳情見 `audit_reports/integrity_latest.json` + `audit_reports/SUMMARY.md`

### A4 · 自動化覆蓋

- **當前:** 9/9 workflow 全自動（GHA 係唯一 data owner）
- **人手介入:** 零（除非 sanity dashboard / audit 亮紅）

---

## B · 已完成里程碑

### B0 · P0 Pivot（2026-04-23, commit `133f714`）
- GHA orchestrates selenium scrapers（`RunAll_Scrapers.py` / `RacingData_Scraper.py`）
- `scraper_utils.py` 加 env override (`CHROMIUM_PATH` / `CHROMEDRIVER_PATH`)
- 7 個 workflow 上線：`capy_pool_a/b`, `capy_race_daily`, `capy_entries`, `capy_trainer_fix`, `capy_fixture_weekly`, `capy_sanity_daily`

### B1 · RacingData hotfix（2026-04-24, commit `7e942a1`）
- 低 RAM flag (`--single-process`, `--max-old-space-size=128`) gated behind `LOW_MEMORY=1` env
- GHA 7GB runner 唔再 Chrome session crash

### B2 · Fixture calendar rewrite（2026-04-24, commits `1a6c51b` / `fa76a88`）
- `FixtureCalendar_Scraper.py` 由 Selenium 換 httpx + regex（zero-pad calmonth）
- Venue-marker pre-filter（防 phantom date）
- Weekly workflow stdlib + httpx 夠，冇 Chrome overhead

### B3 · Step B（2026-04-24, commit `6094164`）
- `scripts/fixture_guard.sh` shared helper, fail-open
- Pool A cron + fixture-aware gate（昨日有賽先跑）
- Entries: tomorrow-race window
- Pool B daily: ±2-day window
- Trainer: past-2-day window
- `capy_sanity_daily.yml` 每日 10:03 HK 跑

### B4 · Sanity fix（2026-04-24, commits `8dec668`, `c9f8e1c`）
- 去除 em-dash（GHA YAML parse 會 silent fail 到 422）
- Multi-line `python3 -c` flatten 做 single-line + single-quote wrap

### B5 · Elo v1.1 self-heal（2026-04-23, commit `a2ac07a`）
- Summarize step `continue-on-error: true`

### B6 · Repo rebrand（2026-04-24）
- 改名：`HKJC-Horse-Racing-Results` → `tianxi-database`
- Description: `天喜數據庫 · 香港賽馬 AI 數據平台`
- 舊 URL GitHub 自動 301 redirect（零 break）
- 新 README.md（面向用戶，每個 scraper 解說清楚）

### B7 · Integrity Audit（2026-04-24, commit `611397d`）
- `tools/data_integrity_audit.py`（10-category）
- `capy_integrity_audit.yml`（11:00 HK，auto-Issue with dedupe，red badge on critical）
- 首日 baseline: 2,587 critical（1,268 horse profiles + 1,268 form_records + 50 race artefacts + 1 jockey）

### B8 · git_sync.py critical fix（2026-04-24, commit `dfb4943`）
- `DATA_DIRS` list 之前漏咗 `"data"` → race_daily 所有 result silently dropped
- 一行 fix。4/19 + 4/22 artefact 即刻 push 成功

### B9 · Phantom fixture strip（2026-04-24, commit `10047ba`）
- 剷走 8 個 2025-08/09 假 fixture（HK 夏季休季）
- 配合 B2 venue-marker filter，防止未來再入

---

## C · Pending — 數據完整性收尾

### C0 · 核心原則 (非可妥協)

> **「數據係命根，唔可以遺漏。」**
>
> 每個 category 必須 100% 齊全：
> - 每場比賽 5 個 artefact (results / commentary / dividends / sectional_times / video_links)
> - 每匹現役馬必須有 profile + form_records + trackwork
> - 每位現役騎師/練馬師必須有 profile + records
> - Fixture cache 必須涵蓋 current year + upcoming 30 日
> - 試閘 / Entries upcoming 必須新鮮

### C1 · 已發現嘅關鍵 data gap (2026-04-24 audit baseline)

| Category | Severity | Gap | 影響 |
|---|---|---|---|
| horse_profiles | critical | **1,268 missing** | 過去 180 日有落場嘅現役馬冇 profile |
| horse_form_records | critical | **1,268 missing** | 同上，連 form 都冇 |
| race_artefacts | critical | 50 missing | 2025-08 有 10 個 race day 某 artefact 缺 |
| jockey_profiles | critical | 1 missing | 1 位現役騎師冇 profile |
| trainer_records | warn | 67 missing | Trainer profile 有，但 records/ dir 空 |
| jockey_records | warn | 5 missing | 5 位 jockey 冇 records |
| entries_upcoming | warn | 1 missing | 1 日 upcoming race 冇 entries |

**Audit tool:** `tools/data_integrity_audit.py`（每日 11:00 HK 自動跑 via `capy_integrity_audit.yml`）
**Output:** `audit_reports/integrity_YYYY-MM-DD.json` + `audit_reports/SUMMARY.md`
**Auto Issue:** Critical 會自動 open Issue 並 label `integrity`

### C2 · Backfill dispatch 進行中

- `capy_pool_a.yml` force=true → HorseData + Trackwork + Injury（修 1,268 missing horse profiles + form_records）
- `capy_race_daily.yml` date=2025-08-07,08-10,08-14,08-17,08-21,08-24,08-28,09-24 → 修 50 race artefact
- `capy_trainer_fix.yml` → 修 67 trainer records（schedule cron 都會自動跑）

### C3 · Gap-fill backfill 策略 (by severity + size)

| Critical gap size | 行動 |
|---|---|
| 0 | All green, 冇嘢做 |
| 1-50 | GHA 下一次 daily delta 自動修 |
| 51-500 | Issue 自動 open，dispatch `capy_pool_a.yml` with `force=true` |
| 501-2000 | Dispatch backfill workflow（feed 具體 horse_no list）|
| > 2000 | Escalation：check scraper health、rate-limit、or HKJC schema change |

### C4 · Audit-driven sanity dashboard integration

`capy_sanity_daily.yml` (每日 10:03 HK) 讀 `audit_reports/integrity_latest.json`，
將 `overall_severity` / `critical_gap_count` 作 top banner render 入 `reports/SANITY.md`。
亮紅時 dashboard 同 audit 會同時通知。

### C5 · Baseline tag 目標

Audit 連續 **7 日** `overall_severity == "ok"` + `critical_gap_count == 0` →
發 `capy-handover-baseline-v1` tag（對應「後端完全 production-ready」節點）。

---

## D · 未來 Roadmap

### D1 · 數據擴展
- [ ] Elo v2：多因子 model（場地、距離、馬場狀態）
- [ ] Trainer stats 完整 scrape（HKJC SPA stats parsing 現時失敗，silently 得 2 col）
- [ ] `horses/profiles/horse_profiles.csv` dynamic column 正規化
- [ ] 退役馬名尾 `(已退役)` suffix 自動 strip
- [ ] **`NewsScraper.py` — 賽馬新聞爬取器**（2026-04-24 frontend directive）
  - 目的：主頁「今日焦點」section 數據源
  - 來源：HKJC News / SCMP Racing / Oriental Daily 馬經 / Google News RSS
  - 輸出：`data/news/YYYY-MM/news_items.csv` (title, url, source, published_at, summary, image_filename, tags) + `data/news/images/<slug>.jpg`
  - Cron：每 6 小時 + 賽馬日前後 1 小時加頻
  - 需配合：image download + compression (Pillow) · dedupe by URL hash · robots.txt 尊重

### D2 · API 層
- [ ] Cloudflare Worker read-only proxy
- [ ] JSONL export（畀 streaming 用家）
- [ ] Parquet mirror（畀 ML pipeline）

### D3 · 下游產品
- [ ] 前端 dashboard（直 fetch raw CSV）
- [ ] 選馬 AI 助手（基於 Elo + Form + Trackwork signal）
- [ ] Backtest framework（評估 rating model 長線準確度）

---

## E · Runbook 快速索引

| 情境 | 檔案 |
|---|---|
| 新人上手 | [README.md](./README.md) |
| 今日系統健康 | [reports/SANITY.md](./reports/SANITY.md) |
| 今日 audit 狀態 | [audit_reports/SUMMARY.md](./audit_reports/SUMMARY.md) |
| 開發日誌 | [BUILD_JOURNAL.md](./BUILD_JOURNAL.md) |
| Data schema 細節 | [DATA_NOTES.md](./DATA_NOTES.md) |
| 本計劃（狀態 + roadmap）| plan.md（本檔）|

### E1 · 手動觸發 workflow

```bash
# Pool A 強制跑（例如 ad-hoc backfill）
gh workflow run capy_pool_a.yml -f force=true

# Race day（特定日期）
gh workflow run capy_race_daily.yml

# Fixture refresh（24 個月）
gh workflow run capy_fixture_weekly.yml

# Integrity audit
gh workflow run capy_integrity_audit.yml
```

### E2 · 查錯順序

1. 查 [`reports/SANITY.md`](./reports/SANITY.md) — 今日狀態一頁睇
2. 查 [`audit_reports/SUMMARY.md`](./audit_reports/SUMMARY.md) — 數據完整性
3. GitHub Actions tab → 過濾 failed run → 睇 log
4. Chrome crash → 確認冇 trigger `LOW_MEMORY` 路徑（GHA 唔應該）
5. Rate limit → 應該唔會（GHA 係 sole scraper）
6. Fixture cache stale → 手動 dispatch `capy_fixture_weekly.yml`

---

*本 plan.md 係 living doc。每個里程碑 landed 後應即時更新。*
