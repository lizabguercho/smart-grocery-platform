# SLM benchmark research log

## 2026-10-02 — Foundation decisions

### Decision: Tier-1 fields are only `is_product` and `category`

**Reason:** SuperCompare silver labels (+ 13 manual overlays) are the
project-accepted category signal. Exclusion phrases give deterministic
non-product gold. `item_name_en` is machine-generated and known to
hallucinate; `manufacture_name` is incomplete and not a brand registry;
ETL quantity/unit fields are structurally present but noisy for pack
equivalence.

**Consequence:** Predictions still request brand / English name /
quantity / unit for qualitative review, but quantitative metrics score
only Tier-1 fields.

### Decision: Stratified category sampling (18/class) + fee slice

**Reason:** Pure random sampling would starve rare classes (Deli &
Salads, Baby) and hide error analysis by category. Soft floor of 18
with seed 42 keeps the set near the real taxonomy while remaining
inspectable (~250 rows).

**Consequence:** Benchmark composition is flatter than the source
labeled distribution; both are recorded in the manifest.

### Decision: Pad non-products with synthetic `np-*` names

**Reason:** Remote `grocery.products` only has ~8 strong fee/voucher
names. Broad markers like `חזרות` false-positive on real yogurt
("להחזרות").

**Consequence:** Non-product gold uses strong markers only, then
deterministic synthetic fee phrases to reach ~30+ examples.

### Decision: Primary model `Qwen/Qwen2.5-0.5B-Instruct`

**Reason:** Same Qwen2.5 instruct family as the translation stack;
0.5B is a realistic laptop baseline; optional sibling 1.5B for
controlled scaling. No new family tonight.

**Consequence:** Experiment ids `qwen25_05b_zero_shot_v1` /
`qwen25_15b_zero_shot_v1`.

### Decision: Constrained decoding off

**Reason:** JSON compliance is itself a measured capability.

### Decision: Never regenerate the frozen benchmark from the runner

**Reason:** Prevent silent train/test leakage and score chasing.

### Decision: Seeded shuffle of frozen row order

**Reason:** Category-sorted CSV made `--limit 5/20` smoke slices
all-Baby, hiding pipeline issues on other classes.

**Consequence:** Final CSV order is `Random(seed+7)` after stratified
sampling; labels unchanged.

### Decision: Coerce category→null when is_product=false at parse time

**Reason:** 0.5B often emits valid JSON with `is_product=false` and a
non-null category. Treating that as a hard schema failure conflated
JSON success with a cross-field rule violation.

**Consequence:** JSON validates; category is cleared for non-products;
wrong `is_product` still hurts Tier-1 metrics.

### Observation from full runs

- **0.5B:** defaults to `is_product=false` on nearly every grocery name
  (0 true product predictions). Parse success high; Tier-1 scores near
  zero.
- **1.5B:** `is_product` F1 ≈ 0.82; category Macro-F1 ≈ 0.07. Scaling
  helps detection more than fine-grained category choice under this
  zero-shot prompt.
- **English:** both models often transliterate or hallucinate
  (`aguz kshu claiy ank 150 gr`). v1 never scored English — see v2.

### Leakage policy

> The frozen benchmark must never be included in future SFT/LoRA
> training datasets.

Exact `item_name` duplicates removed within the sample; semantic
near-duplicate detection deferred.

### Implementation note — reused components

- `CATEGORIES` from `transformer_classifier.py`
- `effective_main_category` / exclusions from `comparable_labels.py`
- `export_labeled_comparable_products.py` (read-only remote join)
- Translation exclusion / Hebrew helpers; Qwen load pattern mirrored
  in a **new** `QwenGroceryUnderstandingModel` (translation untouched)

## 2026-10-02 — v2 translation gold redesign

### Decision: Keep v1 frozen; add human-validated English gold on same IDs

**Reason:** Translation target/evaluation was underspecified.
Transliteration of common Hebrew nouns looked like “output” but was
never judged. Resampling would break comparability with saved
predictions.

**Consequence:** Same 249 `item_code`s; separate
`v2_annotations` / `v2_gold`; re-eval dirs `*__eval_v2` without
overwriting v1 metrics.

### Decision: Annotation assistant ≠ Qwen under test

**Reason:** Avoid using the benchmarked SLM as automatic gold.

**Consequence:** Candidates via `AGENT_MODEL` (pydantic-ai / OpenAI
stack); human review required before gold freeze.

### Decision: Defer LLM-as-judge and COMET

**Reason:** Need gold first; COMET poorly suited as primary metric for
ultra-short grocery SKUs.
