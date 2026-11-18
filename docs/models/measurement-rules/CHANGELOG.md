# Changelog — measurement-rules
Owner: samguercho
Task: Extract package measurements (mass/volume/count) from a Hebrew product title with deterministic rules (system A).
Depends on:
Next step: Rules 0.3.0: N*M multi-packs, count+amount scope rule (guidelines v2.1), trailing-number policy; verify on the merged 200-title dev set.

## 0.2.1 — 2026-11-18 — stage: error-analysis
- **Change:** none in rules logic. Shared `units-v2` adds the alias `ליט` = litre; evaluator `counted_item` leniency and gold conventions `guidelines-v2.1`.
- **Evaluation:** dev exact 81/100 (unchanged). test2 (post-hoc, now development data): presence P/R/F1 81/64/72 %, exact 45/100; random 60: exact 44; targeted 40: exact 1/40, presence recall 58 %.
- **Findings:** rules miss most multi-pack and count+amount entries (targeted recall 58 %); `N*M` with a unit, count-before-amount patterns and trailing numbers are the next rule additions (rules 0.3.0).
- **Next:** rules 0.3.0: `N*M` multi-pack (per_item, package_count N, product noun as counted_item), count+amount scope rule from guidelines v2.1.

## 0.2.0 — 2026-11-14 — stage: error-analysis
- **Change:** one change: count-only entries now fill `counted_item` with the matched noun or unit text (`R_COUNT_UNITS`, `R_COUNT_NOUN`); count words (pair/triple/quad) stay empty, as in the guidelines. Nothing else touched.
- **Why:** the known gap from 0.1.0.
- **Artifacts:** `src/measurement_extraction/rules.py`; predictions `rules_dev.jsonl` (v0.1.0 kept as `rules_dev_v0.1.0.jsonl`); test predictions not regenerated.
- **Evaluation:** dev, same 100 gold items. Presence P/R/F1 80/82/81 % (unchanged); exact titles 81/100 (was 70); joint entry P/R 76/77 % (was 51/52); counted item accuracy on matched 97 %; 9 false measurements on "none" unchanged.
- **Findings:** the gain is only the counted-item field. The evaluator's singular/abbreviation map was built from dev, so this is optimistic. The trailing-number false positives and the recall gap on 24-character titles are untouched.
- **Decision / next:** policies first (see Next step).

## 0.1.0 — 2026-11-01 — stage: error-analysis
- **Change:** first deterministic baseline. Rule ids: `R_NUM_UNIT`, `R_COUNT_UNITS`, `R_COUNT_NOUN`, `R_COUNT_WORD`, `R_TRAILING_NUMBER`. Percent and `N*M` spans are masked. Unit conversion is the shared registry `units-v1`.
- **Why:** baseline for the A/B/C comparison.
- **Artifacts:** `src/measurement_extraction/rules.py`; predictions `research/normalization/predictions/rules_{dev,test}.jsonl`; guidelines `guidelines-v1`; commit: 239a32c.
- **Evaluation:** dev, 100 saved gold items (`research/normalization/reports/dev_eval.md`). Presence P/R/F1 80/82/81 %; exact titles 70/100; 9 false measurements on titles tagged "none" (bare trailing numbers: shades, codes); unit/role/scope 100 % on matched entries; counted item 67 % (never filled by the rules). On the 26 titles of exactly 24 characters presence recall is 64 %.
- **Findings:** the rules were written while reading the first dev titles, so dev numbers are optimistic. Counted item is a known gap, not a reading error. `R_TRAILING_NUMBER` ignores context and is the source of the false positives.
- **Decision / next:** v0.2.0 rule engineering (counted item; trailing-number policy), re-score on the same items.
