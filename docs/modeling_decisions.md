# Modeling decisions — conclusions

Canonical record: [ADR 0006](adr/0006-main-category-classifier.md).
Experiments: [product_classifier_experiments.md](product_classifier_experiments.md).
Error analysis: [product_classifier_error_analysis.md](product_classifier_error_analysis.md).

## Selected model (unchanged)

- **y:** 12 SuperCompare main categories (5,718 labeled products)
- **X:** `item_name` + `manufacture_name` from `grocery.products`
- **Model:** TF-IDF + Linear SVM
- **Test:** accuracy 0.871, Macro F1 0.862

Do not retrain yet. Do not score the ~9,098 unlabeled products yet.
Do not train a Hebrew transformer yet.

## Error analysis conclusions

111 of 858 Test products disagree with SuperCompare (12.9%).

The mass of errors is **Bakery / Snacks / Pantry / Deli** overlapping
(soup almonds, cake mixes, crackers, granola, pasta-as-deli). That is
mostly **category ambiguity**, not a broken SVM.

A smaller slice is **silver-label noise**. Thirteen of those barcodes
now have an approved overlay (see below). Cigarettes stay excluded.

Short or empty names (`ברייק3`, missing manufacturer) are a real
**model limit** of bag-of-words TF-IDF.

**Next:** keep Linear SVM; decide taxonomy/reporting for
Bakery–Pantry–Snacks before any transformer. Do not score the 9,098
until the overlay is used in a new training run.
