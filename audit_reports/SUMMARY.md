# Data Integrity Audit · 2026-05-03

**Overall:** 🟡 `warn`  ·  critical gaps: **0**  ·  warn gaps: 8

**Recommendation:** `monitor_no_block`

## Per-category

| Category | Severity | Expected | Present | Missing | Stale | Notes |
|---|---|---|---|---|---|---|
| race_artefacts | 🟡 warn | 615 | 614 | 1 | 0 | days with any missing artefact: 1 |
| fixtures_cache | 🟢 ok | 1 | 143 | 0 | 0 | total cached race days: 143 |
| horse_profiles | 🟢 ok | 1282 | 1282 | 0 | 0 | total profiles in DB: 5945 |
| horse_form_records | 🟢 ok | 1282 | 1282 | 0 | 0 | total form_records files: 5945 |
| jockey_profiles | 🟢 ok | 47 | 47 | 0 | 0 | total jockey profiles: 64 |
| jockey_records | 🟡 warn | 64 | 59 | 5 | 0 | 5 jockey profiles have no records file |
| trainer_profiles | 🟢 ok | 44 | 44 | 0 | 0 | total trainer profiles: 67 |
| trainer_records | 🟢 ok | 67 | 67 | 0 | 0 |  |
| trial_results | 🟢 ok | 1 | 1 | 0 | 0 | trial rows: 5768 |
| entries_upcoming | 🟡 warn | 3 | 1 | 2 | 0 | 2 upcoming race days lack entries file |
