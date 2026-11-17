# Prompt reviews — measurement-extraction
Category: preprocessing/normalization
Prompt: src/measurement_extraction/prompts.py
Symbol: SYSTEM_PROMPT
Model: Qwen/Qwen3.5-4B, 4-bit MLX, greedy, non-thinking
Model doc: docs/models/measurement-qwen/CHANGELOG.md
Owner: samguercho
Purpose: Extract package measurements (mass, volume, count) from one noisy Hebrew product title as JSON.
Next step: Fix the source_unit contradiction first, then split into (1) span finding + kind (amount / count / bare number) by the model, (2) role/scope/describes assigned by code from the unit registry and cues; then reduce to ≤10 constraints, define "plausible size" and "recognizable unit". One prompt version per change; re-score on dev.
Notes: Evidence beats the score: if error analysis contradicts a review finding, trust the error analysis and record why here. Prompt rounds already spent on the current 100 dev items: 2 (see docs/model_lifecycle.md rule 10).

## 2026-11-14 — actions: FIX-COHERENCE, SPLIT, MOVE-TO-CODE, CLARIFY — validity: valid — tier: small — prompt-sha: b9d56bee8179
- Load: K=13 band 6/10 -> over; P(all pass) at p=.95 is 0.51; ~940 est. tokens
- Dimensions: load=fix coherence=fix ambiguity=fix structure=watch efficiency=watch hygiene=ok
- Measured: not measured (no consistency run yet); dev accuracy exact 66/100, presence F1 92%
- Order of work: FIX-COHERENCE first (one-line change, targets the measured count-in-amount error, cheap to verify), then MOVE-TO-CODE and SPLIT together (they are the same change: role/scope leave the prompt), then CLARIFY. Independent actions; the order is by cost and by the dev error analysis, not by label.
- Decision table: copy (source_text, amount, unit, counted_item); classify (has_measurement, describes, role, scope); multi-hop (role and scope depend on whether the unit resolved and on count presence); no compute.
- [fix][coherence] "copy source_unit only if unit-like text is attached" contradicts "leave source_unit null" for counts; a count word is unit-like text. Likely cause of counts still copied into amount/unit (measured on dev, v0.2.0). Fix: one rule: counts never use source_amount/source_unit.
- [fix][load] 13 constraints for a 4B model. Role/scope of amount entries are deterministic from the unit and cues (rules scored 100% on them); move to code and drop those rules from the prompt.
- [fix][ambiguity] undefined: "plausibly is that size", "normally sold by size or weight", "recognizable unit", "stray letter". Fix: define by rule or list the allowed unit vocabulary.
- [watch][structure] the strictest rules sit in the middle third of the prompt; repeat the null policy at the end.
- [watch][efficiency] the schema restates enum meanings that the rules repeat.
- Comment: hygiene ok: no corpus overlap, no examples. Output-contract failures (unescaped quotes in מ"ל, ק"ג) are a parser/decoding problem, not a prompt problem (qwen 0.3.0).

## 2026-11-14 — actions: CLARIFY — validity: invalid — tier: small — prompt-sha: 69de49c2c327
- Load: K=7 band 6/10 -> risky; historical review of measurement-qwen 0.1.0 (commit 239a32c), done as a back-test
- Dimensions: load=watch coherence=watch ambiguity=watch structure=ok efficiency=ok hygiene=blocker
- Measured: not measured
- [blocker][hygiene] illustrative nouns and a dimension pattern in the schema comments also occur in the dev titles (leakage by the project's rule 9). Removed in 0.2.0.
