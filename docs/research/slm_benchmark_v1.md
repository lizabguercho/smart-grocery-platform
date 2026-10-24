# SLM grocery-understanding benchmark v1

Related: [Documentation map](../README.md) ·
[Research log](slm_benchmark_log.md) ·
[Product name translation](../product_name_translation.md) ·
[ADR 0006 — main-category classifier](../adr/0006-main-category-classifier.md)

## Research question

How well can current Small Language Models perform **structured
understanding** of noisy Israeli supermarket product names, and how do
model size, prompting, and later domain fine-tuning affect performance?

## Motivation

The Smart Grocery catalog mixes Hebrew, Latin, abbreviations, pack
sizes, and non-product fee/voucher lines. Local Qwen translation
experiments showed frequent hallucinations, motivating a controlled
benchmark rather than ad-hoc model selection.

## Tonight's scope

Zero-shot structured extraction only. No RAG, no chat integration, no
LoRA/SFT, no full-catalog translation.

## Benchmark

| Item | Value |
|---|---|
| Version | `slm_grocery_understanding_v1` |
| Path | `data/benchmarks/slm_grocery_understanding_v1.csv` |
| Size | 249 rows (216 products + 33 non-products) |
| Seed | 42 |
| Product sampling | Stratified 18 per SuperCompare main category |
| Category gold | SuperCompare silver + manual overlay; excluded barcodes dropped |
| Non-product gold | Strong fee/voucher markers; padded with synthetic `np-*` names when the DB has too few real fee SKUs |
| Leakage | Frozen `item_code`s must never enter future SFT/LoRA train sets |

Tier-1 auto-eval fields: `is_product`, `category`.

Tier-2 qualitative only: `brand`, `normalized_name_en`, `quantity`,
`unit` (no trustworthy gold for English names or clean brand registry).

## Experimental variables

Tonight: model size (`Qwen/Qwen2.5-0.5B-Instruct`, optional 1.5B).

Held constant: frozen benchmark, `zero_shot_v1` prompt, greedy
generation (`do_sample=False`, `max_new_tokens=256`), same metrics.

Tomorrow (planned): few-shot prompting; domain fine-tuning excluding
this benchmark.

## Metrics

- Parse / JSON schema success — instruction following
- `is_product` accuracy / P / R / F1 — fee vs SKU detection
- Category accuracy / Macro-F1 / per-class — main grocery taxonomy
- Latency mean / median / p95 — practical cost on a laptop

## How to run

```bash
# One-time: rebuild labeled join (read-only remote), then freeze benchmark
PYTHONPATH=. uv run python scripts/export_labeled_comparable_products.py
PYTHONPATH=. uv run python -m src.slm_benchmark.build_dataset --seed 42

# Experiment (optional transformers group)
uv sync --group transformers
PYTHONPATH=. uv run --group transformers python -m src.slm_benchmark \
  --model qwen25_05b --prompt zero_shot_v1 \
  --benchmark slm_grocery_understanding_v1
```

Results land in `experiments/slm_benchmark/<experiment_id>/`.

## Results (2026-10-02)

Shared settings: frozen `slm_grocery_understanding_v1` (n=249),
prompt `zero_shot_v1`, greedy decoding, `max_new_tokens=256`,
`torch_dtype=auto`, `device_map=auto` (MPS).

| Experiment | Parse | is_product acc | is_product F1 | Cat acc | Cat Macro-F1 | Mean lat |
|---|---:|---:|---:|---:|---:|---:|
| `qwen25_05b_zero_shot_v1` | 0.988 | 0.133 | 0.000 | 0.000 | 0.000 | 1.56 s |
| `qwen25_15b_zero_shot_v1` | 0.996 | 0.735 | 0.824 | 0.102 | 0.067 | 4.62 s |

**0.5B:** almost never sets `is_product=true` (0/246 parsed). Accuracy
≈ non-product prior. Category scores collapse.

**1.5B:** much better product detection; category still weak (~10%
accuracy). Common failure: wrong allowed label (e.g. snacks → Frozen,
tea → Bakery). Artifacts under `experiments/slm_benchmark/`.
