# Changelog — measurement-cascade
Owner: samguercho
Task: Rules accept narrowly eligible clean cases; Qwen handles everything else (system C). Whole result of one system per title, no field merging.
Depends on: measurement-rules 0.1.0, measurement-qwen 0.1.0
Next step: Wait for rules and qwen v0.2.0, then re-derive the routing whitelist from dev, report support and errors per whitelist rule, and freeze it before any test evaluation.

## 0.1.0 — 2026-11-01 — stage: error-analysis
- **Change:** first cascade. Whitelist: exactly one number+registered-unit match, amount and unit resolved, no other digits left in the title, no container-capacity word. No match is never trusted as "none".
- **Why:** test whether rules can take the clean cases and cut Qwen calls without hurting accuracy.
- **Artifacts:** `src/measurement_extraction/cascade.py`; predictions `research/normalization/predictions/cascade_{dev,test}.jsonl` (fallback rows reuse the cached Qwen outputs); commit: 239a32c.
- **Evaluation:** dev, 100 saved gold items. Presence P/R/F1 95/86/90 %; exact titles 72/100 (rules 70, qwen 67); 2 false measurements on "none"; 17 of 100 dev titles routed to rules (an estimate of Qwen calls avoided; the benchmark ran Qwen on every title anyway).
- **Findings:** best presence score of the three, but the exact-title differences are within noise on 100 titles (intervals overlap). The whitelist is a draft and unfrozen; no per-rule support table exists yet.
- **Decision / next:** do not tune the whitelist until the components are at 0.2.0.
