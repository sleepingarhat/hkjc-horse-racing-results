# 天喜數據庫 · tianxi-database

HKJC 賽馬數據爬取、CSV 底倉、GitHub Actions 自動調度、D1 同步管道。

## 系統概覽

**生態系統（3 repos）**

| Repo | 角色 | 技術棧 |
|------|------|--------|
| **tianxi-database**（本 repo · public） | HKJC 爬取 · CSV 數據底 · GHA 調度 · D1 同步 | Python + GitHub Actions |
| **tianxi-backend**（private） | D1 + Workers API · ELO 計算 · 複合預測 | Hono + TypeScript + Cloudflare D1 |
| **tianxi-site**（public） | CF Pages 靜態前端 · HKJC 3 層佈局 | Vanilla HTML/CSS/JS |

## 數據規模

- **891 賽馬日** · 8,400 場 · 101,582 行賽果 · 2016–2026（11 年）
- **5,953 匹馬** · 168 位騎師 · 178 位練馬師
- **ELO 快照**：馬匹 81,079 · 騎師 49,200 · 練馬師 47,485（ELO v1.2）
- **往績**：199,941 行 · **傷患**：1,447 行 · **晨操**：104 行（補全中）

## 目錄結構

```
tianxi-database/
├── data/YYYY/          # 每日賽事 CSV（results / commentary / dividends）
├── data/fixtures/      # 賽期日曆
├── horses/             # profiles/ · form_records/ · trackwork/ · injury/
├── jockeys/            # profiles + records
├── trainers/           # profiles（records 待修——HKJC SPA 改版）
├── trials/             # trial_results.csv · trial_sessions.csv
├── entries/            # 排位表（txt 格式）
├── audit_reports/      # 每日完整性審計報告
├── .elo-pipeline/      # Node.js/TypeScript ELO v1.2 計算引擎
├── .github/workflows/  # 17 個 GHA 工作流
└── tools/              # build_manifest.py · data_integrity_audit.py
```

## GitHub Actions 工作流（17 個）

| 工作流 | 職責 | HKT 時間 |
|--------|------|----------|
| `capy_race_daily` | 爬取每日賽果 | 23:30 |
| `capy_pool_a` | 馬匹資料 + 晨操 + 傷患（4 分片並行） | 04:00+1 |
| `capy_pool_b_daily` | 試閘 + 騎師 | 02:00 |
| `capy_entries` | 排位表（週一/二/六） | 20:00 |
| `capy_d1_sync` | 推送賽事資料至 Cloudflare D1 | 00:23 |
| `capy_d1_sync_pool_a` | 推送馬匹/晨操/傷患至 D1 | 05:17 |
| `capy_d1_sync_entries` | 推送排位表至 D1 | 20:43 |
| `elo-post-race` | ELO v1.2 重算 + 推送 D1 | 01:13 |
| `capy_integrity_audit` | 10 類完整性審計 | 11:00 |
| `capy_odds` | 即時賠率快照（每 10 分鐘） | 賽馬日 |
| …其他 | 賽期/SANITY/manifest | 各時 |

## ELO 引擎 v1.2

三軸獨立計算：馬匹（K=28, τ=548d）· 騎師（K=18, τ=730d）· 練馬師（K=11, τ=1095d）  
複合分：`0.7 × 馬匹 + 0.2 × 騎師 + 0.1 × 練馬師`

初始分：本地馬 1500 · 外購馬 1580 · 訪港騎師 1550  
賽季末迴歸（7 月 31 日）：馬匹 2%，騎師/練馬師 5%

## 已知缺口

- **練馬師記錄**：HKJC SPA 改版後 HTML table parser 失效，記錄從未爬取
- **晨操**：104 行（目標 5,000+），補全中
- **賠率快照**：`odds_snapshots` 現時 0 行，`capy_odds` 工作流需調試

## 本地開發

```bash
pip install -r requirements.txt
python RacingData_Scraper.py --date 2026-05-01
python tools/data_integrity_audit.py
```

---

> 內部管理控制台：`tianxi-backend/admin`（需 Bearer token）
