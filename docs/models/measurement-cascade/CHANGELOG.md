# Changelog — measurement-cascade
Owner: samguercho
Task: Rules accept narrowly eligible clean cases; Qwen handles everything else (system C). Whole result of one system per title, no field merging.
Depends on: measurement-rules 0.2.0, measurement-qwen 0.2.0
Next step: Freeze the whitelist with a per-rule support table after rules 0.3.0 and the Qwen scope fix; compare against the gpt-4o reference.

## 0.2.1 — 2026-11-18 — stage: error-analysis
- **Change:** none (whitelist unchanged); re-scored with Qwen 0.4.0 and units-v2.
- **Evaluation:** dev presence P/R/F1 91/91/91 %%, exact 69/100 (Qwen scope regression carries through). test2 (post-hoc, development data): presence 89/95/92 %%, exact 49/100; random 60: exact 44, presence F1 81; targeted 40: exact 5.
- **Reference:** gpt-4o with the identical prompt: dev exact 91/100, test2 exact 63/100 (random 48/60, targeted 15/40), presence F1 99 / 96. See research_log "gpt-4o reference".
- **Next:** freeze the whitelist with a per-rule support table after rules 0.3.0.

## 0.2.0 — 2026-11-14 — stage: error-analysis
- **Change:** none to the whitelist; the fallback now uses measurement-qwen 0.2.0 outputs (component version bump, so a new cascade version). Rules component now 0.2.0 (counted_item only; no routing effect, cascade result identical to the run with 0.1.0 rules: 71/100).
- **Why:** re-score the cascade with the improved Qwen prompt.
- **Artifacts:** `research/normalization/predictions/cascade_dev.jsonl` (test predictions not regenerated, still built from qwen 0.1.0).
- **Evaluation:** dev, same 100 gold items. Presence P/R/F1 92/100/96 % (was 95/86/90); exact titles 71/100 (was 72, noise); 4 false measurements on "none" (was 2); role/scope macro-F1 84 % (was 64 %); 17 of 100 routed to rules.
- **Findings:** the gain comes from Qwen recall and role/scope; exact-title is flat. Whitelist still unfrozen with no per-rule support table.
- **Decision / next:** wait for rules 0.2.0 and qwen 0.3.0, then derive and freeze the whitelist from dev.

## 0.1.0 — 2026-11-01 — stage: error-analysis
- **Change:** first cascade. Whitelist: exactly one number+registered-unit match, amount and unit resolved, no other digits left in the title, no container-capacity word. No match is never trusted as "none".
- **Why:** test whether rules can take the clean cases and cut Qwen calls without hurting accuracy.
- **Artifacts:** `src/measurement_extraction/cascade.py`; predictions `research/normalization/predictions/cascade_{dev,test}.jsonl` (fallback rows reuse the cached Qwen outputs); commit: 239a32c.
- **Evaluation:** dev, 100 saved gold items. Presence P/R/F1 95/86/90 %; exact titles 72/100 (rules 70, qwen 67); 2 false measurements on "none"; 17 of 100 dev titles routed to rules (an estimate of Qwen calls avoided; the benchmark ran Qwen on every title anyway).
- **Findings:** best presence score of the three, but the exact-title differences are within noise on 100 titles (intervals overlap). The whitelist is a draft and unfrozen; no per-rule support table exists yet.
- **Decision / next:** do not tune the whitelist until the components are at 0.2.0.
