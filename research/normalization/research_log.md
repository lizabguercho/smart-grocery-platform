# Research log: Hebrew measurement extraction (experiment step 1)

Task: extract package measurements (mass / volume / count) from noisy Hebrew retail product titles, title only.
Systems: A = rules, B = Qwen3.5-4B prompted zero-shot, C = cascade (rules take clean cases, Qwen the rest).
Model status and changelogs: `docs/MODEL_STATUS.md`, `docs/models/*/CHANGELOG.md`. Lifecycle: `docs/model_lifecycle.md`.

## Status
- **Done:** schema + shared unit conversion; fresh random sample of 200 titles (100 dev / 100 test, seeded, 0 overlap with the 100 earlier-inspected titles); blind annotation UI; 100 dev titles annotated (guidelines v1); rules, Qwen and cascade predictions on all 200; evaluator; dev scores.
- **Not done:** the 100 test titles are **not annotated** and test predictions are **not scored** (test stays hidden until the systems are frozen); no frozen-evaluation lock/results screen; no fine-tuning (no separate training data yet).
- **Dev scores** (100 saved gold items; development numbers, not test results): `research/normalization/reports/dev_eval.md`.

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

## Next
1. Qwen prompt v0.2.0 (counts -> package_count/counted_item), rules v0.2.0 (counted_item), re-score on the same dev items.
2. Annotate the 100 test titles blind, freeze, then run the single final evaluation.
