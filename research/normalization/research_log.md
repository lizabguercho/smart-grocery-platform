# Research log: Hebrew measurement extraction (experiment step 1)

Task: extract package measurements (mass / volume / count) from noisy Hebrew retail product titles, title only.
Systems: A = rules, B = Qwen3.5-4B prompted zero-shot, C = cascade (rules take clean cases, Qwen the rest).
Model status and changelogs: `docs/MODEL_STATUS.md`, `docs/models/*/CHANGELOG.md`. Lifecycle: `docs/model_lifecycle.md`.

## Status
- **Done:** schema + shared unit conversion (units-v2); 200-title dev/test sample (old test retired, never scored); blind annotation UI; dev gold (100, guidelines v1) and test2 gold (100, guidelines v2, human-saved, 22+21 convention fixes logged); rules 0.2.x, Qwen 0.4.0 (experimental) and cascade on dev and test2; gpt-4o reference run on both; evaluator with random/targeted strata.
- **Test2 is now development data** (read for error analysis, informed Qwen 0.3.0/0.4.0). There is currently **no independent test set**; a fresh one is drawn only after systems freeze.
- **Headline (test2, 100 titles, exact title):** rules 45, Qwen 0.4.0 47, cascade 49, **gpt-4o 63**. Targeted 40: 1 / 5 / 5 / 15. Random 60: 44 / 42 / 44 / 48. Dev exact: 81 / 68 / 69 / 91.
- **Known regression:** Qwen 0.4.0 writes `whole_package` on count-only entries (dev scope F1 83 -> 44 %). First fix on the list.

## Layout
- `samples/dev.csv`, `samples/test.csv`, `samples/sample_meta.json`: the drawn sample (immutable; seed, population, hashes in the meta file).
- `gold/annotations.jsonl`: append-only human annotations (latest line per item is current; the `annotator` field marks drafts written by the assistant and confirmed by the human).
- `predictions/{rules,qwen,cascade}_{dev,test}.jsonl`: raw system outputs. `qwen_bf16_dev_partial.jsonl` is an archived 32-title run of the unquantized model.
- `reports/`: generated evaluation output. `guidelines.md`: annotation guidelines v1.
- `research/samples_product.txt` (repo root of research/): the original 100 inspected titles, kept untouched; their codes are excluded from the new sample.

## Reproduce
```bash
PYTHONPATH=. uv run python scripts/draw_measurement_sample.py          # once; refuses to redraw (needs REMOTE_DB_* in .env)
PYTHONPATH=. uv run uvicorn src.measurement_extraction.app:app --port 8765   # annotation page
PYTHONPATH=. uv run python scripts/run_extractors.py --system rules --split dev
# one-off 4-bit conversion of the pinned checkpoint (needs the HF cache copy of Qwen/Qwen3.5-4B @ 851bf6e):
uv run --group mlx python -m mlx_lm convert --hf-path <snapshot dir> --mlx-path ~/.cache/mlx_models/Qwen3.5-4B-4bit-g64 -q --q-bits 4 --q-group-size 64
PYTHONPATH=. uv run --group mlx python scripts/run_extractors.py --system qwen --split dev --batch-size 4 --backend mlx
PYTHONPATH=. uv run python scripts/run_extractors.py --system cascade --split dev
PYTHONPATH=. uv run python scripts/evaluate.py --split dev
PYTHONPATH=. uv run python scripts/run_gpt4o.py --split dev|test2        # reference run, sends titles to OpenAI (needs OPENAI_API_KEY in .env)
PYTHONPATH=. uv run python scripts/draw_measurement_test2.py          # once; the new independent test set (see FROZEN.md)
```

## Decisions and deviations from the brief
- Standalone annotation server (`src/measurement_extraction/app.py`, file-backed, no database, no logic) instead of mounting on `agent_platform`, whose lifespan needs the database and API keys.
- Qwen runs as a **local uniform 4-bit MLX conversion** of the pinned checkpoint (not the unquantized model): bf16 PyTorch on a 16 GB M1 ran at 14-19 s/title and swapped; 4-bit MLX runs at about 4.4 s/title. Quantization changes outputs slightly (1 of 16 titles differed in a check).
- Dev and test were drawn together (200 titles) at the user's request; the brief's "annotate the existing 100 as dev" was replaced by a fresh sample.
- 44 clear-cut dev items were drafted by the assistant from the title only and confirmed unchanged by the human; they are reported separately.
- Predictions on the test split already exist on disk but are not shown by the UI and not scored.

## Findings
- **Titles are truncated at 24 characters.** 42 of 200 sampled titles are exactly 24 characters; `item_name` is plain TEXT and the ETL does not truncate, so the cut is already in the source feed. The size often sits in a separate field on the retailer page. Scores are reported split by "exactly 24 characters".
- First dev comparison: see changelogs. Systematic issues: Qwen puts counts in amount/unit and leaves package_count empty, and does not escape quotes in `מ"ל` (3 invalid-JSON failures on dev); the rules never fill counted_item and flag bare trailing numbers (9 false measurements on "none").
- Limits: 100 dev titles (differences of a few points are noise); rules were written while reading dev titles; the sample is not representative of all retailers.

## Review of the approach (2026-11-14): known weak points
Ranked by how much they can make the system wrong in production.
1. **Structured feed fields were never used as a baseline.** `grocery.products` has `unit_qty`, `quantity`, `unit_of_measure`, `qty_in_package`, `is_weighted` and `manufacture_item_description` (from the retailer XML). Guidelines say "title only", which is right for measuring the extractor but leaves open whether extraction is needed at all, or whether the title should only fill gaps. Their coverage and reliability on the dev items are **unchecked** **Checked 2026-11-14 on the 100 dev items** (feed `unit_qty` + `quantity` converted with the same unit registry, compared with gold): all 100 have the fields populated. Where gold has a mass/volume amount (18 items) the feed agrees on 15 (83 %), one is another family, two have no mass/volume unit. For **counts** (20 items) the feed has the count on only 3: it mostly says "1 unit". On the 56 titles where gold says "no measurement" the feed gives a mass or volume for 28 (50 %), i.e. it supplies sizes the title lacks (truncation, weighted items; `is_weighted` is true on 10). Not verified against ground truth: where feed and title disagree we do not know which is right. Conclusion: the feed is a strong complementary source for mass/volume and weak for counts, so it must be a baseline (system D) and a candidate input to the cascade, not ignored. Query used: `unit_qty, quantity, unit_of_measure, qty_in_package, is_weighted` from `grocery.products` by `item_code`; `unit_of_measure` is the unit-price basis (`100 גרם`), not the package size.
2. **Dev gold does not exercise the hard schema parts.** No dev item has capacity, per-item scope, more than one entry, or count+amount together; 56 of 100 are "none". Role/scope scores are therefore close to trivial, and the cascade/rules scope logic is untested. Multi-packs (`N*M`) are masked as "dimensions" by the rules and described as non-measurements in v0.1.0 prompt wording, which is probably wrong for grocery titles; there is no dev item to show it.
3. **Dev is small and reused.** 100 titles: intervals are about ±9 points, differences between systems are noise. The rules were written reading dev, the prompt was iterated on it, 44 gold labels were drafted by an assistant (same model family as the system family under test) and confirmed. Test (100) is the only clean evidence and is too small to separate close systems.
4. **Invalid JSON is a product failure, not a metric.** 3/100 outputs are unparseable because of unescaped `"` inside `מ"ל`/`ק"ג`, exactly the most common units; the prompt cannot fix this. Needs lenient re-parse or grammar-constrained decoding.
5. **Redundant schema fields invite inconsistent output.** Counts duplicated in amount/unit and package_count; model-supplied `describes` survives even when the unit is unresolved.
6. **Quantization and truncation.** The system is evaluated on 4-bit MLX, not the pinned bf16 checkpoint (1 of 16 titles differed). 21% of titles are cut at 24 characters upstream; the true size is often not in the title at all, so a ceiling on recall exists that no prompt can lift.
7. **Matching/evaluation.** Entry matching uses span overlap, so a wrong span can still match; `counted_item` equivalence is a hand map built from dev; "exact title" is all-or-nothing on 7 fields and is sensitive to the guideline choices (bare numbers).
8. **Cascade whitelist is derived from dev and has no per-rule support table.**

Prompt best practices checked against external guidance (JSON mode needs the word JSON and an explicit schema; small models do better with short, field-by-field rules and a clear null policy; constrained decoding gives validity but can cost accuracy and should be tested; never tune a prompt against the eval set or copy eval items into it, and keep a holdout nobody reads). Our prompt now follows the first three; the last two are why this document asks for more gold and a frozen test.

## Next (ordered)
1. **Qwen 0.4.1:** fix the count-only scope regression (prompt bullet + deterministic post-parse: count-only entry has no scope); re-run dev + test2. Record latency and cost per 1,000 titles in every comparison (see "Cost and latency").
2. **Gold hygiene (needs the annotator):** confirm three test2 items against guidelines v2.1: `100 יח' 2 גרם` (per_item vs the count-before-amount rule), `קמפטאון תרמוס 500 מל+ 3 כוסות` (per_item with no package count), `רוטב שום 30 גר * 128 יח` (describes volume with a gram unit). Re-check dev gold (v1) count+amount items under v2.1.
3. **Merged development set:** treat dev + test2 as one 200-title dev set; document the roles in FROZEN.md. Hold out nothing from it; the final test is a **fresh** 100-title sample drawn only after freezing.
4. **Rules 0.3.0:** `N*M` with a unit, count+amount scope, trailing-number policy; cascade whitelist freeze with per-rule support table.
5. **Fine-tuning (decided 2026-11-18):** labelled **training** set of about 300-500 titles, disjoint from dev and the future test, labelled under the frozen guidelines v2.1 (assistant drafts only for the obvious, human confirms); fine-tune Qwen3.5-4B (LoRA); benefit expected in accuracy and in input tokens (no long instruction prompt). Compare against the gpt-4o reference.
6. **Feed fields as system D** (unit_qty/quantity) with the same evaluator; optional.
7. Run `/prompt-review` on the measurement prompt (its hash changed since the last review) and on the two unreviewed prompts.

## gpt-4o reference (2026-11-18)
Not a shipped system: the same zero-shot prompt (0.4.0, sha256 `7e53c0950aad2b89563c4458478a47a156902f289529368b16e9d9b7bfe94a23`), parser and evaluator, `gpt-4o-2024-08-06`, temperature 0, JSON mode, titles only sent to the API (`scripts/run_gpt4o.py`; predictions `gpt4o_{dev,test2}.jsonl`). 0 invalid outputs.
| | dev | test2 all | test2 random 60 | test2 targeted 40 |
|---|---|---|---|---|
| presence F1 | 99 | 96 | 91 | 99 |
| exact title | 91/100 | 63/100 | 48/60 | 15/40 |
| joint entry P/R | 78/82 | 38/46 | 52/62 | 30/37 |
| unit / role / scope F1 | 100/99/100 | 88/86/74 | 88/80/76 | 83/88/65 |
Reading: even gpt-4o gets only 15/40 targeted titles exactly right, so part of the remaining error is convention and label ambiguity, not model size. This is the milestone to approach.

## Cost and latency (per title; to be reported in every system comparison)
| system | latency | cost |
|---|---|---|
| rules | under 1 ms | 0 |
| Qwen3.5-4B 4-bit MLX, 16 GB M1 | 7.0 s (dev), 8.4 s (test2) median/mean, about 43-70 output tokens, batch 4 | no per-call cost (local hardware, electricity only) |
| gpt-4o (API, 20 sequential calls) | 1.1 s median (1.8 s max) | about 830 input + 40-60 output tokens per title; **about USD 2.5-2.7 per 1,000 titles** at an assumed list price of 2.50 USD per 1M input and 10 USD per 1M output tokens (assumption, not verified against the live price list) |
Fine-tuning removes most of the 830 input tokens (the instruction prompt), which would cut both the Qwen latency and any hosted-model cost.
