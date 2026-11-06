# Changelog — measurement-qwen
Owner: samguercho
Task: Extract package measurements from a Hebrew product title with a prompted Qwen3.5-4B (system B), zero-shot.
Depends on:
Next step: Prompt engineering v0.2.0: counts go in package_count/counted_item (never amount/unit); count-only entries have no role or scope. Re-run all 200 titles, re-score on the same 100 dev items.

## 0.1.0 — 2026-11-01 — stage: error-analysis
- **Change:** first full baseline inference. Zero-shot prompt (no demonstrations), prompt sha256 `69de49c2c3270a6086900578c16c9ecbe0723c09ea2e5e95a3bcaaa969405096`. Model `Qwen/Qwen3.5-4B` revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`, run as a local uniform 4-bit MLX conversion (group size 64, mlx-lm 0.32.2). Greedy decoding, `enable_thinking=False`, max 256 new tokens, one attempt per title, batch size 4.
- **Why:** baseline for the A/B/C comparison. 4-bit MLX because bf16 PyTorch on a 16 GB M1 ran at 14–19 s/title and swapped; MLX 4-bit runs at about 4.4 s/title.
- **Artifacts:** `src/measurement_extraction/{qwen,prompts}.py`; predictions `research/normalization/predictions/qwen_{dev,test}.jsonl`; a partial bf16 run is archived as `qwen_bf16_dev_partial.jsonl` (32 dev titles, not scored); guidelines `guidelines-v1`; commit: 239a32c.
- **Evaluation:** dev, 100 saved gold items. Presence P/R/F1 95/80/86 %; exact titles 67/100; 3 invalid-JSON failures (counted as misses); 2 false measurements on "none"; role macro-F1 54 %, scope 57 %; amount and package count accuracy on matched entries 57 %; counted item 89 %.
- **Findings:** (1) on count titles it writes the count into source amount/unit and leaves package_count empty, then adds role/scope; (2) it does not escape the quote in `מ"ל`/`ק"ג`, which breaks strict JSON; (3) one prompt line (JSON-escape instruction) was added after a 5-title smoke test and before this run. Presence recall on 24-character (truncated) titles is 93 %.
- **Decision / next:** v0.2.0 prompt engineering aimed at (1); the quote escaping stays a measured failure (a lenient re-parse can be a separate condition).
