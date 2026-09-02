# Main-category classifier experiments

This is the first modeling pass: **12 SuperCompare main categories**,
classical TF-IDF models only. Subcategories (55 classes) and the ~9,098
unlabeled comparable products are **out of scope**.

Run (from the repo root, local database required):

```bash
PYTHONPATH=. .venv/bin/python3 -u scripts/run_category_classifier_experiments.py
```

The script does **not** write to any database table. It saves tables under
`data/processed/` (gitignored).

Related: [ADR 0006](adr/0006-main-category-classifier.md) ·
[error analysis](product_classifier_error_analysis.md) ·
[supercompare_labeling.md](supercompare_labeling.md)

---

## What X and y are

Each row is one labeled comparable product (barcode in both
`grocery.price_comparison` and SuperCompare).

**y (the answer we want the model to copy)** is the SuperCompare
**main category** (`Dairy & Eggs`, `Snacks & Sweets`, …). There are
**12** of these. We do not predict subcategory here.

**X (what the model is allowed to read)** is text only:

| Experiment | X |
|---|---|
| A | `item_name` from `grocery.products` |
| B | `item_name` plus `manufacture_name` from `grocery.products` |

Missing manufacturer values (null, blank, `-`, `לא ידוע`, and similar
placeholders) are replaced with an **empty string**. The product is
kept; it just has no manufacturer words.

We **do not** use:

- IDs (`item_code`) — they are barcodes, not grocery meaning
- SuperCompare `manufacturer`, product name, or `source_url`
- prices or cheapest chain
- subcategory or `include_in_analysis`
- classification metadata

Those columns would either leak the label, not exist at prediction time
for unlabeled products, or not describe what the product *is*.

We use all **5,718** labeled comparable products, including the 25
name/category mismatches that are flagged `include_in_analysis=false`.
They are a small amount of label noise.

---

## Why test name vs name + manufacturer

The product name is the obvious signal (`חלב 3%`). Manufacturer can add
a brand cue (`תנובה` often dairy, `סוד` often personal care).

We already checked that manufacturer is **present at similar rates** in
labeled (91.3%) and unlabeled (87.9%) products, so Experiment B is a
fair preview of scoring the 9,098 later. If manufacturer had been mostly
missing on unlabeled rows, we would not have used it.

---

## Train vs validation vs test

Think of a school test:

| Split | Share | n | Role |
|---|---:|---:|---|
| **Train** | 70% | 4,002 | The model studies these labeled examples |
| **Validation** | 15% | 858 | We compare the 6 experiments and pick a winner |
| **Test** | 15% | 858 | One final score after the winner is chosen |

Rules we followed:

1. Fit TF-IDF and the classifier **only on Train**.
2. Choose features + model using **Validation Macro F1**.
3. Look at **Test** only for the winner. Test did not influence the
   choice.

If we used Test to pick the model, the Test number would be optimistic
(we would have peeked at the exam while choosing).

**Stratification** means we keep the same *mix of categories* in each
split. If 19% of labeled products are Pantry, about 19% of Train,
Validation, and Test are Pantry too. Without this, a random split could
put almost all of tiny **Deli & Salads** (94 products) into Train, and
Validation would not be a fair check.

`random_state=42` makes the split repeatable: the same barcodes go to
the same split every run.

### Category counts in each split

| Category | Train | Validation | Test | Total |
|---|---:|---:|---:|---:|
| Pantry & Cooking | 768 | 165 | 164 | 1,097 |
| Personal Care & Hygiene | 582 | 125 | 125 | 832 |
| Snacks & Sweets | 505 | 108 | 108 | 721 |
| Household & Cleaning | 430 | 92 | 92 | 614 |
| Beverages | 385 | 83 | 82 | 550 |
| Dairy & Eggs | 362 | 78 | 78 | 518 |
| Frozen | 252 | 54 | 54 | 360 |
| Bakery | 225 | 48 | 48 | 321 |
| Meat & Fish | 171 | 37 | 37 | 245 |
| Fresh Produce | 160 | 34 | 35 | 229 |
| Baby | 96 | 20 | 21 | 137 |
| Deli & Salads | 66 | 14 | 14 | 94 |
| **All** | **4,002** | **858** | **858** | **5,718** |

Deli & Salads has only **14** validation and **14** test rows. Baby has
about **20**. Their precision/recall can jump a lot if a few products
are wrong. Treat those class scores as noisy.

---

## What TF-IDF does

The model cannot read Hebrew sentences as a person does. TF-IDF turns
each product’s text into a long list of numbers, one number per word
(token) that appeared in Train.

- **TF (term frequency):** words that appear in *this* product get a
  higher score.
- **IDF (inverse document frequency):** words that appear in *many*
  products (for example a generic word) get a lower score. Rare,
  distinctive words get a higher score.

We used sklearn’s default `TfidfVectorizer()` (word tokens, no extra
tuning). Vocabulary is learned on **Train only**, then applied to
Validation/Test. That way Test cannot invent words that secretly help
the model.

Experiment B is the same idea: manufacturer words are extra tokens in
the same bag (`חלב 3% תנובה`).

---

## The three models (simple picture)

All three take the TF-IDF numbers and pick one of 12 categories.

**Logistic Regression (baseline).** Draws a weighted vote per category:
each word has a weight such as “this word pushes toward Dairy.” The
category with the highest score wins. It is the usual first model for
text.

**Linear SVM.** Also uses word weights, but it tries to put a *wide
gap* between the winning category and the others. It often works well
on high-dimensional TF-IDF.

**Multinomial Naive Bayes.** Treats words as independent counts and
asks “which category usually contains these words?” It is fast and
simple, but the independence assumption is rough, and it often lags on
this kind of data.

No hyperparameter search in this pass (`max_iter` is only so the
solvers can finish).

---

## Accuracy vs Macro F1

**Accuracy** is “what fraction of products got the right category?”
If the model is great on Pantry (1,097 products) and weak on Deli (94),
accuracy still looks good.

**Macro F1** computes F1 (a blend of precision and recall) **per
category**, then **averages the 12 scores equally**. Deli counts as
much as Pantry. That is why Macro F1 is the **main metric** here.

- **Precision:** of products the model *called* Deli, how many really
  were Deli?
- **Recall:** of products that *really are* Deli, how many did the
  model find?

---

## Validation results (all 6 experiments)

Same Train, same Validation, six fits.

| Features | Model | Validation Accuracy | Validation Macro F1 |
|---|---|---:|---:|
| `item_name` | TF-IDF + Logistic Regression | 0.801 | 0.748 |
| `item_name` | TF-IDF + Linear SVM | 0.844 | 0.816 |
| `item_name` | TF-IDF + Multinomial Naive Bayes | 0.723 | 0.591 |
| `item_name` + `manufacture_name` | TF-IDF + Logistic Regression | 0.835 | 0.806 |
| `item_name` + `manufacture_name` | **TF-IDF + Linear SVM** | **0.872** | **0.857** |
| `item_name` + `manufacture_name` | TF-IDF + Multinomial Naive Bayes | 0.754 | 0.626 |

### Did manufacturer help?

**Yes.** On every model, adding `manufacture_name` raised Macro F1:

| Model | Name only | Name + manufacturer | Change |
|---|---:|---:|---:|
| Logistic Regression | 0.748 | 0.806 | +0.058 |
| Linear SVM | 0.816 | 0.857 | +0.041 |
| Naive Bayes | 0.591 | 0.626 | +0.036 |

Keep manufacturer as a feature. Still allow empty manufacturer at
prediction time.

### Which model won?

**TF-IDF + Linear SVM** with `item_name` + `manufacture_name`.

It had the best validation Macro F1 (**0.857**) and the best validation
accuracy (**0.872**). Logistic Regression with manufacturer was second
(0.806 Macro F1). Naive Bayes was last on both feature sets.

---

## Final Test results (winner only)

Setup: `item_name` + `manufacture_name`, Linear SVM, trained on Train
only.

| Metric | Test |
|---|---:|
| Accuracy | **0.871** |
| Macro F1 | **0.862** |

Test is almost the same as validation, which is a good sign: we did not
overfit the choice to one unlucky Validation draw.

### Per-category Test scores

| Category | Test n | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Personal Care & Hygiene | 125 | 0.968 | 0.960 | 0.964 |
| Beverages | 82 | 0.929 | 0.951 | 0.940 |
| Household & Cleaning | 92 | 0.895 | 0.924 | 0.909 |
| Fresh Produce | 35 | 0.889 | 0.914 | 0.901 |
| Meat & Fish | 37 | 0.889 | 0.865 | 0.877 |
| Baby | 21 | 0.944 | 0.810 | 0.872 |
| Frozen | 54 | 0.870 | 0.870 | 0.870 |
| Dairy & Eggs | 78 | 0.827 | 0.859 | 0.843 |
| Pantry & Cooking | 164 | 0.818 | 0.848 | 0.832 |
| Snacks & Sweets | 108 | 0.807 | 0.815 | 0.811 |
| Deli & Salads | 14 | 0.909 | 0.714 | 0.800 |
| Bakery | 48 | 0.800 | 0.667 | 0.727 |

### Where it struggles

**Bakery** is the weakest (F1 0.727, recall 0.667). On Test, bakery
products were often sent to **Pantry & Cooking** (7) or **Snacks &
Sweets** (6). That is a real grocery overlap (bread vs pantry flour,
pastries vs snacks).

**Deli & Salads** looks better on F1 (0.800) but recall is 0.714: 4 of
14 deli products went to **Pantry**. With n=14, one extra error moves
the metric a lot.

**Pantry** is the “magnet” class (largest). Several other categories
leak into it.

**Personal Care**, **Beverages**, and **Household** are strong: names
and brands in those aisles are distinctive.

The confusion matrix CSV is
`data/processed/classifier_test_confusion_matrix.csv` (rows = true
category, columns = predicted).

---

## What we are not doing yet

- Not classifying the ~9,098 unlabeled comparable products
- Not training 55 subcategories
- Not adding a Hebrew transformer
- Not writing predictions to `grocery.product_classification`
- Not rebalancing / downsampling categories

Next decision: whether a Hebrew transformer is worth the extra
complexity, given Linear SVM already at ~0.86 Macro F1 on Test. See
[ADR 0006](adr/0006-main-category-classifier.md).
