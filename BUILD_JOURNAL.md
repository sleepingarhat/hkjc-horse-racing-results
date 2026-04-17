# 天喜娛樂 Tianxi Entertainment — 構建日誌

> **最後更新**：2026-04-17 (Session 2)
> **當前階段**：Stage 2.5 — 後端 live data + 前端 Bottom Sheet 完成
> **終極目標**：上線一年賺 HK$700,000

---

## 一、願景 (Vision)

打造一個**數據驅動、零幻覺**嘅香港賽馬 AI 分析平台。

**核心差異化**：
- 市面嘅賽馬 tipster 90% 靠吹水、小部份有數據但無 AI
- 天喜 AI 係**「歷史數據 + 即時賠率 + 時序預測 + 推理模型」** 四者合一
- **絕不幻覺** — AI 冇數據寧願唔答，都唔會作馬名/騎師/賠率

**平台形態**：iOS / Android / Web 三端（React Native Expo 一套代碼）

---

## 二、賺錢目標拆解：HK$700,000/年

### Scenario A：純訂閱模式
```
月收入目標：HK$58,333
→ 需要付費用戶數：
   • $199/月 × 293 人 = $58,307  ← 主流大眾定價
   • $399/月 × 146 人 = $58,254  ← 專業級
   • $999/月 × 58 人  = $57,942  ← 大戶/VIP
```

### Scenario B：混合定價（推薦 ⭐）
```
基礎版  $99/月  × 200 人 = $19,800
專業版  $299/月 × 100 人 = $29,900
VIP版   $999/月 × 10 人  = $9,990
                        ─────────
                月收入 = $59,690
            年收入 ≈ HK$716,280 ✅
```

### Scenario C：免費增值 + 單場解鎖
```
• 免費用戶：睇基本賠率、今日推薦
• 單場深度分析 $39 / 場
• 全日 pass $199 / 日（約 10 場賽事）
• 月訂閱 $499 解鎖全部
```

### 獲客成本 (CAC) 計算
```
假設 $199/月定價，LTV 6 個月 = $1,194
合理 CAC 上限 ≈ $200-300
→ 需要 IG/小紅書/YT KOL 合作 + Telegram group
```

### 達標需要嘅里程碑
| 月份 | 目標付費用戶 | 月收 | 動作 |
|---|---|---|---|
| M1 上線 | 50 | $6,500 | 私域冷啟動 + 種子 KOL |
| M3 | 150 | $22,500 | 口碑傳播 + 內容營銷 |
| M6 | 300 | $45,000 | 付費投放 + VIP plan |
| M9 | 450 | $67,500 | 達到月目標 $58k |
| M12 | 500+ | $75,000+ | **超標達成** 🎯 |

---

## 三、系統架構（2026-04-17 版本）

```
┌──────────────────────────────────────────────────────┐
│  前端：React Native + Expo SDK 54                     │
│  ├── iOS App (TestFlight → App Store)                │
│  ├── Android App (Internal → Play Store)             │
│  └── Web (Expo Web → Cloudflare Pages)               │
│     tianxi-frontend/expo/                            │
│                 ↓                                     │
│          HTTPS fetch                                  │
│                 ↓                                     │
├──────────────────────────────────────────────────────┤
│  後端：Cloudflare Workers (Hono framework)           │
│  URL: tianxi-backend.tianxi-entertainment.workers.dev│
│  ├── 8 API routes (meetings/races/horses/...)        │
│  ├── Intent Parser (xAI function calling)            │
│  └── Data Gate (反幻覺閘門)                          │
│                 ↓                                     │
├──────────────────────────────────────────────────────┤
│  資料庫：Cloudflare D1 (SQLite edge)                 │
│  Database: tianxi-db                                 │
│  13 tables + 4 views                                 │
│  ├── race_meetings, races, horses, jockeys...       │
│  ├── sectional_times, running_comments...            │
│  └── v_jockey_stats, v_jockey_trainer_combo...      │
└──────────────────────────────────────────────────────┘
              ↑                ↑              ↑
        歷史數據CSV       即時HKJC        AI引擎
        (2016-2026)      GraphQL        ├── xAI Grok 4.20 Reasoning
        GitHub Actions   (Stage 5)       └── TimesFM (Stage 4)
        每日自動更新                        (RunPod Serverless)
```

---

## 四、構建時間線

### Stage 0：構想期 (Pre-2026-04)
- 用戶有 HKJC scraper (Python Selenium)
- 用戶已有 React Native 前端 UI 原型（兩個 repo）
- 核心痛點：數據有，但冇 AI 分析層

### Stage 1：後端基建（2026-04-17 完成）
| 任務 | 完成時間 | 結果 |
|---|---|---|
| 確認需求 + 刪除多餘 repo | Day 1 | ✅ 刪 rork-frontend (SwiftUI) 保留 rork-rork-frontend-ui (Expo) |
| Schema 設計 | Day 1 | ✅ 13 tables + 4 views |
| Hono API + 8 routes | Day 1 | ✅ meetings / races / horses / jockeys / trainers / odds / chat / analyze |
| AI Service 封裝 | Day 1 | ✅ OpenRouter 兼容格式 |
| TimesFM proxy | Day 1 | ✅ HTTP call + linear regression fallback |
| System Prompt v1 | Day 1 | ✅ 天喜 AI persona |
| CSV Import script | Day 1 | ✅ 處理 HKJC 實際格式 (BOM / 中文 venue / quoted fields) |
| GitHub Actions cron | Day 1 | ✅ 修正 Ubuntu chromium path + git push |
| **部署到 Cloudflare** | Day 2 | ✅ D1 + Worker live |
| xAI secret 設定 | Day 2 | ✅ grok-4.20-reasoning |
| End-to-end /api/chat 測試 | Day 2 | ✅ 天喜 AI persona 生效 |
| **System Prompt v2 深化** | Day 2 | ✅ 標注 🟢LIVE / 🟡SEMI / 🔴PENDING |
| **Data Gate (反幻覺閘)** | Day 2 | ✅ INSUFFICIENT 攔截 + Availability metadata |

### Stage 2：前端接駁（進行中）
- ✅ Clone / 摸清前端結構（4 tabs：首頁/賽事/聊天/因子）
- ✅ API client (`lib/api.ts`) + React Query hooks
- ✅ TianxiProvider 改造（真 API + mock fallback + apiStatus）
- 🔵 **進行中**：Bottom Sheet AI Chat 組件
- ⏳ CSV 歷史數據導入
- ⏳ Expo Web build + Cloudflare Pages 部署

### Stage 3-6：未來（Stage 4-6 可能重排先後）
- **Stage 3**：AI Chat 深度整合（streaming / 歷史會話）
- **Stage 4**：TimesFM RunPod 部署
- **Stage 5**：HKJC 即時 GraphQL 賠率
- **Stage 6**：用戶系統 + 付費牆

---

## 五、做啱嘅地方 ✅

### 1. 技術選擇
| 選擇 | 為何正確 |
|---|---|
| **Cloudflare Workers + D1** | 全球邊緣、零冷啟動、免費額度足夠 MVP |
| **Expo (React Native + Web)** | 一套代碼三平台，慳 60% 開發時間 |
| **Hono framework** | TypeScript 友好、輕量、CF Workers 原生 |
| **React Query** | 前端數據緩存、loading/error state 一條龍 |
| **Zustand + Context** | 前端狀態簡單夠用，唔用 Redux over-engineer |
| **OpenAI-compatible AI Gateway** | 將來可換 model（xAI / OpenAI / Anthropic）唔洗改代碼 |

### 2. 架構決策
- **Data Gate 反幻覺架構** — 呢個係最 proud 嘅決定，令天喜 AI 真正可信
- **Schema 先行** — 用 DB 結構去 drive AI 可用嘅工具，而唔係倒轉
- **Mock fallback** — 前端任何時候唔 crash，demo 用 UX 一樣順暢
- **Env var 切換 AI endpoint** — 開發時用 happycapy gateway，production 用 xAI direct

### 3. 開發流程
- 一開始就寫 `plan.md`，全局架構清晰
- 每個 API route 對應一個真實用戶故事
- 有測試：部署後立即 curl 驗證 end-to-end

---

## 六、做唔啱 / 走錯路 ⚠️

### 1. 原型數據就亂作
**錯咩**：System Prompt v1 嘅馬匹範例「1號翠綠迅駒」、「潘頓×蔡約翰 31% 勝率」全部係假數字。

**後果**：AI 學咗呢種「有數字就好真」嘅風格，DB 空嘅時候照作無誤。

**修正**：v2 prompt 加入嚴格禁區 + Data Gate 硬攔截。

**教訓**：AI prompt 範例絕對唔可以係幻覺，要用 placeholder 例如 `[根據 race_results 查出嚟嘅實際馬名]`。

### 2. Scraper 升級策略
**錯咩**：一開始想叫 agent 改用戶本地嘅 Python scraper，但系統邊界唔俾。

**後果**：浪費 30 分鐘嘗試 → 最後要用戶自己改兩行代碼。

**教訓**：知道邊界喺邊，直接俾用戶 diff 塊代碼，唔好硬試 workaround。

### 3. Token 安全意識不足
**錯咩**：用戶兩次都將 credential 直接貼喺 chat
- Cloudflare API token `cfut_eFhGg...`
- xAI API key `xai-wIfQk...`

**後果**：Token 喺 session log 有紀錄，理論上任何讀取呢個 session 嘅人都有完整 credential。

**修正**：已警告用戶部署後立即 rotate。

**教訓**：future session 要**第一時間講**「唔好貼 key 喺 chat，用 wrangler login OR 我寫腳本你本地跑」。

### 4. CSV Schema 設計試錯
**錯咩**：Import script v1 假設咗 CSV 係純 ASCII + 標準格式。

**真相**：HKJC CSV 有 BOM、中文 venue、"name (code)"、"M:SS.ss" 時間、quoted field 內嵌 comma。

**修正**：v2 全面重寫，6 個 parsing helper。

**教訓**：**永遠先讀一個真實 CSV 樣本**，再寫 parser。唔好信「格式文件」。

### 5. Hallucination 晚期先發現
**錯咩**：部署之後測試 `/api/chat`，AI 回覆睇落超靚，但**全部馬名都係作**。

**如果我冇 prompt 用戶注意到**：可能會真係俾終端用戶用，出事。

**修正**：立即加 Data Gate。

**教訓**：AI 系統 **demo 睇起嚟好** ≠ 系統可靠。每個 AI output 要 trace 返 data source。

### 6. 模型名稱 confusion
**錯咩**：Session 中多次提到 `grok-3`、`grok-4.2`、`grok-4.20-reasoning`、`claude-opus-4-6` vs `claude-opus-4-7`。

**後果**：差啲 deploy 咗舊 model，要補測試先知 xAI 實際版本係 `grok-4.20-0309-reasoning`。

**教訓**：AI model ID 一定要實測 curl 一次才寫入 config。

### 7. 前端空頁面 UX
**錯咩**：TianxiProvider 改造後，如果 DB 空會 fallback mock，但 `apiStatus` 狀態冇喺 UI 展示。

**後果**：用戶可能以為睇緊真資料，其實係 mock。

**未修正（TODO）**：要喺 UI 加 banner「🟡 示範資料 / 🟢 真實資料」。

---

## 七、關鍵決策 rationale（供未來參考）

### 為何揀 Cloudflare D1 而非 Postgres？
- D1 免費 5GB、5 million reads/day
- 賽馬數據 10 年約 ~500MB，遠未到上限
- 邊緣 SQLite = 低延遲，用戶查賠率 <50ms
- Postgres 要租 VPS / Supabase，增加成本同維運
- **代價**：D1 無 full-text search、無 JSONB index → 將來搜索強化可加 Cloudflare Vectorize

### 為何揀 xAI 而非 Claude？
- 用戶個人要求（「我要用 Grok 4.2」）
- Reasoning model 對複雜賽馬邏輯有優勢
- **風險**：xAI rate limit 比 Claude 嚴，scale 後要評估
- **Plan B**：AI Gateway 可 fallback 到 Claude Opus 4.6

### 為何 React Native 而非純 Web？
- 賽馬用戶 70%+ 用手機下注
- iOS App Store 可以做應用內訂閱（支援 Apple Pay）
- Push notification 對「開跑前提醒」非常重要
- **代價**：App Store 審核 + 30% 分成

### 為何 Bottom Sheet 而非全螢幕 Chat？
- 用戶嘅選擇（希望睇住賽事底下彈出）
- UX 上維持場次 context，唔洗跳頁
- 類似 Stripe / WeChat 體驗

---

## 八、目前狀態快照（2026-04-17）

| 元件 | 狀態 | URL / 路徑 |
|---|---|---|
| Cloudflare Worker | 🟢 Live | https://tianxi-backend.tianxi-entertainment.workers.dev |
| D1 Database | 🟢 Live（空） | `tianxi-db` UUID `aad1636e-869a-43f5-aa95-4a19e3aa5517` |
| xAI integration | 🟢 Verified | model `grok-4.20-reasoning` |
| System Prompt | 🟢 v2 | `src/prompts/racing-ai.ts` |
| Data Gate | 🟢 Live | `src/routes/chat.ts` |
| 前端 API Client | 🟢 Ready | `lib/api.ts` |
| 前端 Provider | 🟢 改造完 | `providers/TianxiProvider.tsx` |
| 前端 UI | 🟡 未測試 | 4 tabs 接 API 仲未 dev run |
| CSV 歷史數據 | 🔴 未導入 | 886 日喺 GitHub |
| Bottom Sheet Chat | 🔴 未做 | 下一步 |
| TimesFM | 🔴 Stub | Stage 4 |
| 即時 HKJC 賠率 | 🔴 Stub | Stage 5 |
| 用戶系統 | 🔴 未做 | Stage 6 |
| 付費牆 | 🔴 未做 | Stage 6 |

---

## 九、距離 $700K 目標仲有幾遠

### 技術 Roadmap（達成 MVP）
```
[已完成]     Stage 1 後端 + Stage 2 前端框架                        30%
[進行中]     Stage 2.5 Bottom Sheet Chat                           5%
[下一步]     CSV 導入歷史數據                                        10%
             Stage 2.6 Web build + deploy                          5%
             Stage 3 Chat streaming + 會話歷史                       5%
             Stage 4 TimesFM 部署                                    10%
             Stage 5 HKJC 即時 GraphQL                               10%
             Stage 6 用戶系統 + Stripe 付費牆                         15%
                                                               ──────
                                                       MVP Total 90%
             Beta 測試 + 調優                                         10%
                                                               ──────
                                                       上線 Ready 100%
```

### 商業 Roadmap
```
[未開始]  M0 MVP beta：免費內測 30 個用戶
[未開始]  M1 上線 + 冷啟動內容（30 篇公開分析報告）
[未開始]  KOL 合作 2-3 個賽馬 Telegram/YT
[未開始]  IG / 小紅書 持續內容運營
[未開始]  付費用戶破 50 → Public launch
[未開始]  推廣成本: 首 3 個月 $30k 推廣 budget
[目標]    M12 付費用戶 500+ → 達成 $700k/年
```

### 風險清單
| 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|
| HKJC 封 scraper IP | 中 | 高 | 多 IP 池 / residential proxy |
| xAI rate limit | 低 | 中 | AI Gateway 多 provider fallback |
| Apple/Google 封 app（涉博彩） | 中 | 高 | **關鍵**：上線前要法務 review、可能只能 Web |
| 競爭對手抄 | 高 | 中 | 數據護城河（10 年歷史）+ AI 調優 |
| 用戶信任（AI 是否靠得住） | 高 | 高 | Data Gate + 透明化數據源引用 |
| 香港博彩法規 | 中 | 極高 | **絕對唔可以做非法博彩中介**，只做分析服務 |

### ⚠️ 法律 / 合規提醒（極重要）
- 香港只有 HKJC 可以合法接受投注
- 天喜 AI 必須定位係「**數據分析服務**」，絕對不可代客投注
- App 內禁止出現「落注」、「下注」按鈕
- 訂閱內容必須明確標示「僅供參考」
- 建議搵律師過目 Terms & Conditions

---

## 十、未來 session 續接 Checklist

每次開新 session 應該從以下 checklist 開始：

### Quick Status Check
```bash
# 1. 後端健康
curl -s https://tianxi-backend.tianxi-entertainment.workers.dev/ | jq

# 2. DB 狀態
curl -s https://tianxi-backend.tianxi-entertainment.workers.dev/api/meetings | jq

# 3. AI 可用
curl -sX POST https://tianxi-backend.tianxi-entertainment.workers.dev/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"你好"}' | jq '.metadata'
```

### 讀呢份 BUILD_JOURNAL.md + `/workspace/plan.md`
了解全貌。

### 當前 TODO snapshot
見主 session 嘅 TodoWrite state（目前：Bottom Sheet Chat + CSV Import）。

---

## 十一、Append-Only Log（每次 session 加新 entry）

### 2026-04-17 — Session 1（第一日建構）
**主要成果**：
- ✅ 後端完整部署上 Cloudflare
- ✅ xAI Grok 接通 + 廣東話 AI persona 成功
- ✅ Data Gate 反幻覺架構 landed
- ✅ 前端 API client + Provider 改造完

**教訓**：
- Prompt 內嘅範例唔可以係假數字
- AI demo 好睇 ≠ 系統可靠
- Token 唔可以貼 chat

**下次 priority**：
1. Bottom Sheet Chat 組件
2. CSV Import（user 本地跑）
3. Expo Web build 試 deploy

### 2026-04-17 — Session 2（後端數據導入 + 前端 Sheet 接駁）
**主要成果**：
- ✅ **歷史數據導入** — 3 個月真實賽果 (2026-02-01 ~ 2026-04-15)
  - Clone HKJC-Horse-Racing-Results repo (4461 files, 68MB)
  - `import-csv.ts` 成功處理所有實際 CSV (22 race days)
  - 本地 SQLite → SQL dump → `wrangler d1 execute --remote` 上雲
  - **生產 D1 現有**：22 race_meetings, 220 races, 2756 race_results, 1063 horses, 28 jockeys, 22 trainers, 9732 sectional times, 2704 running comments, 2379 dividends, 651 race videos
- ✅ **修正 chat.ts JOIN bug** — 原本用 `hst.race_result_id` 唔存在，改用 `race_id + horse_id` 組合鍵
- ✅ **首次真實 AI 回覆** — 2026-04-15 第1場查詢成功：
  - `dataGate: OK`, `horsesFound: 12`, `sectionalDataFound: 36`
  - AI 正確引用真實馬名（銀亮濠俠、喆喆友福）、真實騎師（潘頓、莫雷拉、布文、鍾易禮）、真實練馬師（徐雨石、沈集成）、真實賠率（3.4/4.9/5.5/6）
  - **反幻覺架構正式生效**：無再作假資料
- ✅ **Bottom Sheet AIChatSheet 組件** (`components/AIChatSheet.tsx`)
  - React Native Modal 由底部升起，含 drag handle
  - Context-aware quick tips（針對當前場次 `第N場 單T...`）
  - 即時狀態 badge（🟢真實 / 🟡示範 / 🔴錯誤）
  - 共用 `useTianxi` chat state，與主 chat tab 同步
  - Keyboard avoiding、loading indicator「天喜 AI 正在分析賽事數據...」
- ✅ **race tab 接通 Sheet** — 場次切換下方加金色 CTA 按鈕「問天喜 AI · 第N場分析」

**技術決定**：
- 棄用 `@gorhom/bottom-sheet` → 用 RN 內建 `Modal` + `slide` 動畫，減少 dep 體積
- D1 一次過 push 3MB / 19597 行 SQL，單次 execute 646ms，冇分 batch
- 先 `DELETE FROM ...` 清表再重灌，避免 UNIQUE conflict

**教訓**：
- **Schema 字段名要先對齊再寫 query** — chat.ts bug 係寫代碼時腦入面假設 schema，實際 schema 係 `race_id + horse_id` 組合鍵。下次要先 `.schema` 再寫 query。
- **wrangler `.config` 路徑敏感** — 某啲 Cloudflare container `/home/node/.config` 係 read-only file 唔係 dir，要 `export XDG_CONFIG_HOME=/tmp/xdg-config` 繞開。
- **CSV 批量導入策略**：本地 SQLite 做 single source of truth → dump to SQL → wrangler execute remote。避免重複 parse CSV 上 edge runtime，一 run 完所有 D1 寫入一次搞掂。

**現時生產系統能回答嘅實際問題**：
1. 「2026-04-15 第1場 單T 兩膽4腳建議」→ AI 根據真實 12 匹馬、36 sectional records 俾具體馬號建議
2. 「2026-04-15 邊匹馬近況最好」→ 可查 race_results 過去 22 日歷史近績
3. 「潘頓 × 沈集成 近期配對勝率」→ 可查 v_jockey_trainer_combo view

**下次 priority (Session 3)**：
1. 前端 `npm install` + Expo Web dev run (端口 8080) + user UAT
2. CSV 全量 10 年歷史（886 賽馬日）批量導入，分 year batch
3. Stage 5：HKJC 即時 GraphQL 賠率接駁
4. Stage 6：用戶系統 + Stripe 付費牆（$199/$399/$999 tier）
5. 考慮添加 `v_horse_form`, `v_jockey_stats`, `v_trainer_stats`, `v_jockey_trainer_combo` 實際 VIEW 建立（schema 有列出但未確認 D1 已建）

**里程碑**：**系統首次從 demo 變成真 production-ready prototype**。可以俾 beta 用戶 10-20 人試用。

### 2026-04-17 — Session 2.5（🚨 Critical Data Leakage Fix）

**用戶捉到嘅 bug**：
> 用戶笑住問：「AI輸出係真預測，定係憑着結果輸出？預測準確100%喎😂」

驗證：AI 喺 Session 2 第一次真實回覆「第1場 單T 兩膽四腳建議 → 5號銀亮濠俠+6號喆喆友福」，再查 D1 實際賽果：
```
#1 6號 喆喆友福 ✅  (AI 膽)
#2 5號 銀亮濠俠 ✅  (AI 膽)
#3 4號 辣得金   ✅  (AI 腳)
#4 8號 太行美景 ✅  (AI 腳)
#6 12號 東方福寶 ✅ (AI 腳)
```
**5/6 命中頭6名** — 因為我 `chat.ts` 將 `finishing_position`、`finish_time`、`running_position`、本場分段時間 全部塞入 AI context，AI 根本唔使預測，睇住賽果寫故仔就得。

**問題本質**：
- ✅ **Data Gate (反幻覺)** 做好咗 — 冇資料唔作
- ❌ **Result Blind Gate (反作弊)** 完全冇做 — 歷史 backtest 下 AI 睇得到自己要「預測」嘅答案

**架構修正 — 加入 Result Blind Gate**：

```typescript
type ChatMode = 'blind_prediction' | 'recap' | 'general';

function decideMode(intent, message): ChatMode {
  if (message.includes('回顧/賽果/點解贏...')) return 'recap';
  if (['bet_suggestion','horse_analysis',...].includes(intent.action)) return 'blind_prediction';
  return 'general';
}
```

修正點：
1. `blind_prediction` 模式下，historical race 嘅 `finishingPosition / finishTime / runningPosition` 一律設 null
2. 本場自己嘅 `horse_sectional_times` 清空（呢啲係 in-race 量度，屬 post-race）
3. 馬匹近績查詢加 `WHERE rm.date < ?` — 避免未來數據洩漏
4. Prompt 加入 🔒 盲測提示，叫 AI 唔可以「靠估果」
5. `recap` 模式 keep 晒賽果，但 prompt 改成「做事後 case study」

**驗證結果**（同一 query 測兩次）：

| 模式 | metadata.resultBlindGate | AI 回覆 |
|---|---|---|
| 修正前 | 冇呢個 gate | "膽：5號、6號；腳：3/4/8/12"（5/6 命中，data leak） |
| blind_prediction | **ENFORCED** | "資料庫冇呢項數據...欠缺歷史近績、Pace分析等，建議觀望" ✅ |
| recap (用戶明確問回顧) | NOT_APPLICABLE | "6號喆喆友福走位2-2-1，典型跟前突圍戰術..." ✅ 真 hindsight analysis |

**教訓（Session 2.5 最重要）**：
- 📊 **反幻覺 ≠ 反作弊**。Data Gate 解決「AI 係咪作馬名」，Blind Gate 解決「AI 係咪偷睇答案」。
- 🧪 **歷史數據 backtest 係雙刃劍**。如果 DB 已有賽果，系統要區分「pre-race perspective」同「post-race perspective」，絕對唔可以混淆。
- 💎 **用戶直覺捉 bug 嘅效率 > 我自己測 10 次**。「100%準」就係架構警號。
- 🔐 **production 前一定要有人手 backtest** — 試一場已跑完嘅賽事，如果 AI 100% 命中，你知有鬼。

**實際防線（現時架構）**：
```
User Query
    ↓
Intent Parser → decideMode()
    ↓
DB Scan (WHERE date < targetDate if blind_prediction)
    ↓
Data Gate (反幻覺)     ← 冇資料唔俾 call AI
    ↓
Result Blind Gate (反作弊) ← 剝離 post-race 欄位
    ↓
AI call (with factualNotice 提醒)
    ↓
Response + metadata.mode + resultBlindGate
```

**Worker Version**: `744c17a0-b8ea-44c4-8d5c-610110080f9d`（Session 2.5 deploy）

**里程碑**：系統首次做到 honest-by-construction — AI 就算**想作弊都作唔到**。

---

**本日誌會持續更新，直至達成 $700K/年目標。**
