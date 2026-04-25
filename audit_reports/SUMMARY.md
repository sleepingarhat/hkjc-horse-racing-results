# Data Integrity Audit · 2026-04-25

**Overall:** 🔴 `critical`  ·  critical gaps: **2557**  ·  warn gaps: 73

**Recommendation:** `replit_fallback_required`

## Per-category

| Category | Severity | Expected | Present | Missing | Stale | Notes |
|---|---|---|---|---|---|---|
| race_artefacts | 🟢 ok | 600 | 600 | 0 | 0 |  |
| fixtures_cache | 🟢 ok | 1 | 143 | 0 | 0 | total cached race days: 143 |
| horse_profiles | 🔴 critical | 1282 | 4 | 1278 | 0 | 1278 horses raced in last 180d have NO profile; total profiles in DB: 1886 |
| horse_form_records | 🔴 critical | 1282 | 4 | 1278 | 0 | 1278 recent-cohort horses have NO form_records file; total form_records files: 1899 |
| jockey_profiles | 🔴 critical | 45 | 44 | 1 | 0 | 1 jockeys raced recently but NO profile; total jockey profiles: 64 |
| jockey_records | 🟡 warn | 64 | 59 | 5 | 0 | 5 jockey profiles have no records file |
| trainer_profiles | 🟢 ok | 38 | 38 | 0 | 0 | total trainer profiles: 67 |
| trainer_records | 🟡 warn | 67 | 0 | 67 | 0 | 67 trainer profiles have no records file |
| trial_results | 🟢 ok | 1 | 1 | 0 | 0 | trial rows: 5609 |
| entries_upcoming | 🟡 warn | 2 | 1 | 1 | 0 | 1 upcoming race days lack entries file |

### 🔴 horse_profiles — sample missing (first 20)

```
D075
E058
E061
E175
E184
E301
E321
E356
E392
E403
E413
E430
E432
E434
E435
E436
E448
E459
E471
E472
```

### 🔴 horse_form_records — sample missing (first 20)

```
D075
E058
E061
E175
E184
E301
E321
E356
E392
E403
E413
E430
E432
E434
E435
E436
E448
E459
E471
E472
```

### 🔴 jockey_profiles — sample missing (first 20)

```
---
```
