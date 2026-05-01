# Data Integrity Audit · 2026-05-01

**Overall:** 🔴 `critical`  ·  critical gaps: **1**  ·  warn gaps: 74

**Recommendation:** `gha_next_delta_will_fix`

## Per-category

| Category | Severity | Expected | Present | Missing | Stale | Notes |
|---|---|---|---|---|---|---|
| race_artefacts | 🟢 ok | 610 | 610 | 0 | 0 |  |
| fixtures_cache | 🟢 ok | 1 | 143 | 0 | 0 | total cached race days: 143 |
| horse_profiles | 🟢 ok | 1288 | 1288 | 0 | 0 | total profiles in DB: 5945 |
| horse_form_records | 🟢 ok | 1288 | 1288 | 0 | 0 | total form_records files: 5945 |
| jockey_profiles | 🔴 critical | 48 | 47 | 1 | 0 | 1 jockeys raced recently but NO profile; total jockey profiles: 64 |
| jockey_records | 🟡 warn | 64 | 59 | 5 | 0 | 5 jockey profiles have no records file |
| trainer_profiles | 🟢 ok | 44 | 44 | 0 | 0 | total trainer profiles: 67 |
| trainer_records | 🟡 warn | 67 | 0 | 67 | 0 | 67 trainer profiles have no records file |
| trial_results | 🟢 ok | 1 | 1 | 0 | 0 | trial rows: 5768 |
| entries_upcoming | 🟡 warn | 2 | 0 | 2 | 0 | 2 upcoming race days lack entries file |

### 🔴 jockey_profiles — sample missing (first 20)

```
---
```
