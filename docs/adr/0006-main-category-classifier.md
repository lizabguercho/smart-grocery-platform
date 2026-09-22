# 0006. Main-category classifier (TF-IDF + Linear SVM)

## Status

Accepted

Related: [product_classifier_experiments.md](../product_classifier_experiments.md) ·
[supercompare_labeling.md](../supercompare_labeling.md) ·
[ADR 0004](0004-product-categorization-and-training-sample.md)

## Context

ADR 0004 required SuperCompare silver labels first, then a simple
classifier for comparable products with no barcode match. After the
full crawl join, that labeled set is **5,718** of **14,816** comparable
products. About **9,098** remain unlabeled. The taxonomy has **12**
main categories and **55** subcategories.

The 5,718 rows already meet the ADR 0004 overall sample target
(about 2,000–5,000). Deli & Salads is thin (94 labeled products). A
55-class subcategory model is not justified yet.

Manufacturer completeness is similar in labeled vs unlabeled
(`grocery.products.manufacture_name`: 91.3% vs 87.9%). SuperCompare’s
manufacturer column is filled on labeled rows and empty on unlabeled
rows, so it cannot be a production feature.

The project is a Data Analyst portfolio. The classifier exists to label
leftovers for category-level price analysis, not to become an ML
research stack.

## Decision

Train a **12-class main-category** model on the 5,718 SuperCompare
labels. Defer subcategories and unlabeled scoring until this classical
baseline is accepted.

### Target and features

- **y:** SuperCompare main category (12 classes).
- **X tested:** `item_name` vs `item_name` + `manufacture_name`, both
  from `grocery.products`.
- Missing manufacturer → empty string.
- Do **not** use SuperCompare manufacturer, IDs, prices, subcategory,
  URLs, or classification metadata.

### Split and metric

One stratified 70 / 15 / 15 split (`random_state=42`) on all 5,718
labeled products. Same barcodes in every experiment. No downsampling.

| Split | n | Used for |
|---|---:|---|
| Train | 4,002 | Fit TF-IDF and the classifier |
| Validation | 858 | Compare experiments; pick winner |
| Test | 858 | Score the winner only |

**Main metric:** Macro F1 (imbalanced classes). Accuracy is reported
alongside. Test is not used to choose features or models.

### Models compared

Baseline: TF-IDF + Logistic Regression.

Alternatives: TF-IDF + Linear SVM, TF-IDF + Multinomial Naive Bayes.

sklearn defaults aside from `max_iter`. No grid search.

### Selected setup

Manufacturer **helped** every model on validation Macro F1
(+0.04 to +0.06).

| Features | Logistic Regression | Linear SVM | Naive Bayes |
|---|---:|---:|---:|
| `item_name` | 0.748 | 0.816 | 0.591 |
| `item_name` + `manufacture_name` | 0.806 | **0.857** | 0.626 |

**Keep** `item_name` + `manufacture_name`.

**Selected model:** TF-IDF + Linear SVM.

Untouched Test: accuracy **0.871**, Macro F1 **0.862**. Weakest classes:
Bakery (F1 0.727), Deli & Salads (F1 0.800, n=14), Snacks & Sweets
(F1 0.811). Narrative, per-class tables, and how to rerun:
[product_classifier_experiments.md](../product_classifier_experiments.md).

### Transformer vs scoring leftovers

A Hebrew transformer is **not** required for the published analysis.
Linear SVM already reaches ~0.86 Test Macro F1. A transformer would
need to beat that on Bakery / Deli / Pantry overlap at a much higher
setup cost. Unlabeled comparables (~9,098) are not scored as
SuperCompare gold in the dashboard extract.

## Rejected alternatives

- **Name-only features.** Worse Macro F1 on every model.
- **SuperCompare manufacturer as a feature.** Missing on unlabeled
  products by construction.
- **Naive Bayes as the production model.** Lowest Macro F1 on both
  feature sets.
- **Logistic Regression as the production model.** Solid baseline;
  Linear SVM was better on the same split.
- **55-class subcategory model first.** Sixteen subcategories are
  sparse; main category is the analysis grain we need first.
- **Train on unlabeled rows or mix Test into model selection.** Would
  leak the hold-out and invent labels.
- **Downsample large classes.** Throws away real Pantry/Personal Care
  volume; Macro F1 already treats classes equally.
- **Hebrew transformer as the first model.** ADR 0004 rejected deep
  learning as the first approach. Classical TF-IDF was run first;
  transformer remains an optional later comparison.

## Consequences

- The classical baseline for leftover comparable products is
  **TF-IDF + Linear SVM** with database name and manufacturer.
- Silver SuperCompare labels remain the source of y. The 25 known
  mismatches stayed in the 5,718; they are a small amount of noise.
- Predictions are **not** written to `grocery.product_classification`
  by this decision. Promotion of SuperCompare labels and later model
  scores stay separate reviewed steps.
- Update this ADR when the transformer question is decided, when
  unlabeled products are scored, or when a subcategory model starts.

## Later update (2 September 2026) — Test error analysis

Untouched Test: **111 / 858** mistakes (12.9%). The model was not
retrained.

Most common pairs: Snacks→Pantry (8), Bakery→Pantry (7),
Pantry→Dairy (7), Pantry→Snacks (7), Bakery→Snacks (6). Pantry is the
magnet class.

Conclusion: errors are **mostly aisle overlap** (Bakery / Pantry /
Snacks / Deli) plus some **SuperCompare label noise** (the model is
sometimes more reasonable than y). TF-IDF is weak on very short names.

## Later update (2 September 2026) — approved overlay

Thirteen obvious SuperCompare errors were approved. They are stored in
`src/product_classification/manual_category_corrections.csv` (not in
the SuperCompare crawl CSV, not in PostgreSQL yet). Pall Mall
`5208049015312` is **not** recoded; it remains in `EXCLUDED_ITEM_CODES`.

Effective y: overlay if present, else SuperCompare. Grocery analysis
also drops denylist barcodes. Historical Test scores (0.871 / 0.862)
were measured on uncorrected SuperCompare labels.

Details: [product_classifier_error_analysis.md](../product_classifier_error_analysis.md).

## Later update (September 2026) — Hebrew tokenizer experiment

AlephBERT was used to inspect token lengths on labeled comparable
products. Fixed 12-class label IDs live in
`src/product_classification/transformer_classifier.py`. The production
classifier remains **TF-IDF + Linear SVM**. The transformer extra is
optional (`uv sync --group transformers`) and is not required to
rebuild the published analysis.
