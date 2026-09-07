# Modeling decisions — conclusions

Canonical record: [ADR 0006](adr/0006-main-category-classifier.md).
Experiments: [product_classifier_experiments.md](product_classifier_experiments.md).
Error analysis: [product_classifier_error_analysis.md](product_classifier_error_analysis.md).

## Selected model (unchanged)

- **y:** 12 SuperCompare main categories (5,718 labeled products)
- **X:** `item_name` + `manufacture_name` from `grocery.products`
- **Model:** TF-IDF + Linear SVM
- **Test (uncorrected SuperCompare y):** accuracy 0.871, Macro F1 0.862
- **Test (14 obvious recodes on the same split):** accuracy 0.885,
  Macro F1 0.878, Weighted F1 0.884

All 14 recodes were in Test, none in Train. The fitted SVM is therefore
the same model; the gain is almost entirely cleaner Test gold, not a
new decision surface. Macro F1 **+0.016** is a small evaluation bump,
not a material model improvement.

Do not score the ~9,098 unlabeled products yet. Do not train a Hebrew
transformer yet.

## Manufacturer completeness (dashboard)

Field: `grocery.products.manufacture_name` (not SuperCompare
`manufacturer`). Missing = null, blank, `-`, `לא ידוע`, and similar
placeholders. All 14,816 comparable barcodes exist in `products`.

| Population | n | Present | Missing | Unique names | Present % |
|---|---:|---:|---:|---:|---:|
| Labeled comparable | 5,718 | 5,222 | 496 | 1,075 | 91.3 |
| Unlabeled comparable | 9,098 | 8,000 | 1,098 | 1,703 | 87.9 |

Gap: unlabeled **−3.4 pp**. SuperCompare manufacturer is **95.3%**
present on labeled rows and empty on unlabeled rows, so it is not a
dashboard or model field.

Manufacturer was kept as a classifier feature, with empty string for
missing values.

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
Bakery–Pantry–Snacks before any transformer. The obvious-recode
retrain did not change Train, so it is not a reason to score the 9,098
yet.
