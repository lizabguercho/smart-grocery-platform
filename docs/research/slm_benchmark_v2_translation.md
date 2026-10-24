# SLM benchmark v2 — translation gold & evaluation

Related: [v1 benchmark](slm_benchmark_v1.md) ·
[Research log](slm_benchmark_log.md) ·
[Documentation map](../README.md)

## Why v2 exists

Initial zero-shot experiments (`qwen25_05b_zero_shot_v1`,
`qwen25_15b_zero_shot_v1`) asked the model for `normalized_name_en`, but:

1. the frozen v1 CSV had **no English gold**;
2. English was **never scored** (Tier-2 qualitative only);
3. the prompt did not distinguish natural English from Hebrew→Latin
   transliteration.

Example from the frozen population (`item_code=7290117906422`):

| | Text |
|---|---|
| Hebrew | `אגוז קשיו קלוי ענק 150 גרם` |
| Desired | `Jumbo Roasted Cashews 150 g` |
| Qwen 0.5B | `Aguz Shvay Klevye Nekhuyot 150 Grm` |
| Qwen 1.5B | `aguz kshu claiy ank 150 gr` |

That is a methodological finding, not something to hide. **v1 artifacts
stay frozen.** v2 keeps the **same 249 `item_code`s** and redesigns gold
annotations + evaluation around semantic fidelity and SKU-information
preservation.

## Task definition

> Translate an Israeli supermarket product name from Hebrew or mixed
> Hebrew/English into a **natural English** grocery product name while
> preserving all information necessary to identify the SKU.

Natural word-order variants are equivalent. Phonetic rendering of
ordinary Hebrew grocery vocabulary is **not** an acceptable translation.

## Versioning

| Artifact | Role |
|---|---|
| `data/benchmarks/slm_grocery_understanding_v1.csv` | Immutable Hebrew population |
| `data/benchmarks/slm_grocery_understanding_v2_annotations.csv` | Candidate + gold workspace |
| `data/benchmarks/slm_grocery_understanding_v2_gold.csv` | Human-frozen gold (after review) |
| `experiments/.../qwen25_*_zero_shot_v1/` | Original predictions + v1 metrics (keep) |
| `experiments/.../qwen25_*_zero_shot_v1__eval_v2/` | Re-evaluation metrics (new) |

Candidates from a cloud annotation assistant are **never** auto-copied into
gold. Status: `unreviewed` → `accepted` / `corrected` / `excluded`.

## Evaluation layers

1. **Deterministic:** `is_product`, silver `category`, plus qty/unit/pack/%
   vs gold after conservative unit normalization.
2. **Attribute preservation:** null-aware match on brand, product_type,
   variant, quantity, unit, pack_count, percent.
3. **LLM-as-judge:** deferred until gold exists; transliteration of common
   nouns = `major_error`.
4. **COMET / BLEU / ROUGE:** not primary; COMET deferred; no BLEU/ROUGE.

## Current gold status

A **partial smoke gold** (`v2_gold.csv`, 6 hand-authored rows including the
cashew example) exists so re-eval plumbing can be verified. It is **not**
the final human-validated set. Full workflow:

```bash
PYTHONPATH=. uv run python -m src.slm_benchmark.annotate_candidates
# Local labeling UI (preferred) — http://127.0.0.1:8765/
PYTHONPATH=. uv run python -m src.slm_benchmark.labeling
# Or terminal CLI:
PYTHONPATH=. uv run python -m src.slm_benchmark.review_annotations
PYTHONPATH=. uv run python -m src.slm_benchmark.freeze_gold_v2 --force
PYTHONPATH=. uv run python -m src.slm_benchmark.eval_translation \
  --predictions experiments/slm_benchmark/qwen25_15b_zero_shot_v1/predictions.jsonl --force
```

The labeling desk is task-plugin based (`LabelingTask` registry). Today it
ships `translation_v2`; new labeling jobs register without rewriting the UI.

Partial re-eval outputs (do not treat as final scores):
`experiments/slm_benchmark/qwen25_*_zero_shot_v1__eval_v2/`.

## Leakage

Frozen v1/v2 `item_code`s must never enter future SFT/LoRA training sets.

