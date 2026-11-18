---
name: prompt-review
description: Review a prompt file for task load, coherence, ambiguity, structure, efficiency and leakage, and return independent recommended actions, a validity flag and line-referenced findings (split it, fix a contradiction, move computation to code). Use when asked to review, score, audit or simplify a prompt, or before changing a prompt version.
argument-hint: <path-to-prompt> [--tier small|mid|frontier] [--corpus file.csv ...]
allowed-tools: Bash(python3 .claude/skills/prompt-review/scripts/prompt_metrics.py:*), Bash(PYTHONPATH=. uv run python scripts/build_prompt_status.py:*), Read, Grep, Edit, Write
---

# Prompt review

Never edit the prompt itself. The only files this skill writes are the prompt's `REVIEWS.md` and the generated `docs/PROMPT_STATUS.md`. The output is a set of independent actions plus recommendations a person can act on, not a number to maximise. Background, thresholds and sources: [references/rubric.md](references/rubric.md). Read it before judging.

## Inputs
- `$ARGUMENTS`: path to the prompt (`.py` with a `*PROMPT*` string, `.md` or `.txt`), optional `--tier` (target model size: `small` ≤8B, `mid`, `frontier`; default `small` for this project's local Qwen3.5-4B) and optional `--corpus` CSVs (dev/test data, for the leakage check).
- If the prompt has a guideline, schema or validator elsewhere (this project: `research/normalization/guidelines.md`, `src/measurement_extraction/schema.py`), read it too: prompt-versus-guideline mismatch is a coherence defect.

## Steps
1. Run the measurements and keep the JSON:
   `python3 .claude/skills/prompt-review/scripts/prompt_metrics.py <path> --tier <tier> [--corpus ...]`
   For measurement prompts always pass `--corpus research/normalization/samples/dev.csv research/normalization/samples/test.csv`.
2. Read the whole prompt with line numbers (file line = extracted line + `line_offset` - 1).
3. Build the **decision table**: one row per thing the model must decide or produce, classified as Copy, Classify, Recall, Compute, Multi-hop or Judge (definitions in the rubric). Mark which decisions depend on another decision's result.
4. Judge the six dimensions with the rubric: **Load, Coherence, Ambiguity, Structure, Efficiency, Hygiene** (hygiene = leakage, versioning, testability). Every finding needs: a quote or line number, the evidence type (`measured` from the script, `judged`, `literature`), a severity (`blocker`, `fix`, `watch`) and a concrete fix. No finding without a location; no fix without a reason.
5. Decide **actions** and **validity** separately. They are independent: there is no ladder where one outranks another.
   - **Actions** (zero or more; from `SPLIT`, `MOVE-TO-CODE`, `FIX-COHERENCE`, `CLARIFY`, `REORDER`, `TRIM`, or `NONE`). Each comes from its own dimension: `SPLIT` from load or chained decisions; `MOVE-TO-CODE` from Compute decisions or derivable fields; `FIX-COHERENCE` from contradictions or prompt/schema/guideline mismatch; `CLARIFY` from ambiguity; `REORDER` from structure; `TRIM` from redundancy. A high-load coherent prompt gets `SPLIT` only; an easy but incoherent prompt gets `FIX-COHERENCE` only; neither is "better".
   - **Order of work** is not given by the labels. Order by expected effect on the model's measured behaviour: first the actions that target errors the project has actually measured (error analysis), then the cheapest to verify, then the rest. If consistency was measured (see rubric, "Measured evidence"), use `consistency.diagnose`; otherwise say "not measured" and do not pretend a static review predicts performance.
   - **Validity**: `invalid` when scores from this prompt cannot be trusted (real dev/test data in the prompt, or an output contract the parser cannot read by design); otherwise `valid`.
6. **Record it** (always, same place): the prompt's registry file is `docs/prompts/<category>/<prompt-id>/REVIEWS.md`, listed in `docs/PROMPT_STATUS.md`. Category is one of `preprocessing`, `classification`, `agentic`, `evaluation` and follows where the prompt sits in the pipeline (a prompt that cleans or normalises data before it is stored is `preprocessing`; a chat/tool-using agent is `agentic`). If the file does not exist, create it with the header (copy `docs/prompts/preprocessing/measurement-extraction/REVIEWS.md`: `Category`, `Prompt`, optional `Symbol`, `Model`, optional `Model doc`, `Owner`, `Purpose`, `Next step`, `Notes`); ask the user only if the category is unclear. Insert the new entry **at the top** (newest first) in exactly this form, with `prompt-sha` = first 12 hex chars of the sha256 of the prompt text (the registry computes it; the build script prints a mismatch as "changed since review"):
   ```
   ## YYYY-MM-DD — actions: <A, B, ... or NONE> — validity: <valid|invalid> — tier: <small|mid|frontier> — prompt-sha: <12 hex>
   - Load: K=<n> band <comfortable>/<risky> -> <within|risky|over>; <one-line context>
   - Dimensions: load=<s> coherence=<s> ambiguity=<s> structure=<s> efficiency=<s> hygiene=<s>   (s = ok|watch|fix|blocker)
   - Measured: <"not measured" or consistency=<0-1> accuracy=<0-1> n=<items> k=<samples> variants=<n> models=<tiers>>
   - Order of work: <why this order, citing measured errors>
   - [severity][dimension] <finding with line and fix>
   - Comment: <anything the next person needs>
   ```
   Update the header `Next step` (the single most valuable next action) and keep human `Notes`. Then run `PYTHONPATH=. uv run python scripts/build_prompt_status.py` and `--check`. Get the prompt-sha with `PYTHONPATH=. uv run python -c "from pathlib import Path; from src.prompt_registry.extract import *; print(fingerprint(extract_prompt(Path('<path>'), '<SYMBOL or None>')[0]))"`.
7. Report in the format below. Mention where the entry was recorded. Then say how to check the recommendation worked: which metric in the project's evaluation should move, and that the change is one prompt version (see `docs/model_lifecycle.md`, rules 3, 9, 10).

## Report format
```
Actions (independent, in recommended order): <list or NONE>   Validity: <valid|invalid>   Tier: <tier>   Prompt: <path> (<tokens> est. tokens)
Load: K=<constraints> vs band <comfortable>/<risky> -> <within|risky|over>; P(all pass) at p=.95: <x>
Decision table: <table>
Dimension   Status(ok/watch/fix/blocker)   Findings count
Measured evidence: <consistency/accuracy, or "not measured" and what run would measure it>
Findings (most impact first):
  1. [<severity>][<dimension>][<evidence>] L<line>: "<quote>" -> <fix> (why: <one line>)
Recommended order of work: <1-3 steps>
How to verify: <metric, version bump>
Limits: <what this review cannot know>
```
Keep it short: lead with the actions and the one lever with the most expected gain.

## Rules for the reviewer
- The numbers are heuristics from the literature, not measurements of this model. Say so, and prefer the project's own error analysis when it contradicts the score.
- Do not invent examples to illustrate a fix inside a prompt that must stay example-free; use placeholders.
- When recommending a split, name the sub-prompts, what each outputs, and which parts become deterministic code.
- Do not praise to fill space. If it is fine, say NONE and stop.
