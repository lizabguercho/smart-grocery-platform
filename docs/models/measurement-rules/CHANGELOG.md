# Changelog — measurement-rules
Owner: samguercho
Task: Extract package measurements (mass/volume/count) from a Hebrew product title with deterministic rules (system A).
Depends on:
Next step: Rule engineering v0.2.0: fill counted_item from the matched noun, then re-score on the same 100 dev titles (decide the bare-trailing-number rule against guidelines v1 first).

## 0.1.0 — 2026-11-01 — stage: error-analysis
- **Change:** first deterministic baseline. Rule ids: `R_NUM_UNIT`, `R_COUNT_UNITS`, `R_COUNT_NOUN`, `R_COUNT_WORD`, `R_TRAILING_NUMBER`. Percent and `N*M` spans are masked. Unit conversion is the shared registry `units-v1`.
- **Why:** baseline for the A/B/C comparison.
- **Artifacts:** `src/measurement_extraction/rules.py`; predictions `research/normalization/predictions/rules_{dev,test}.jsonl`; guidelines `guidelines-v1`; commit: 239a32c.
- **Evaluation:** dev, 100 saved gold items (`research/normalization/reports/dev_eval.md`). Presence P/R/F1 80/82/81 %; exact titles 70/100; 9 false measurements on titles tagged "none" (bare trailing numbers: shades, codes); unit/role/scope 100 % on matched entries; counted item 67 % (never filled by the rules). On the 26 titles of exactly 24 characters presence recall is 64 %.
- **Findings:** the rules were written while reading the first dev titles, so dev numbers are optimistic. Counted item is a known gap, not a reading error. `R_TRAILING_NUMBER` ignores context and is the source of the false positives.
- **Decision / next:** v0.2.0 rule engineering (counted item; trailing-number policy), re-score on the same items.
