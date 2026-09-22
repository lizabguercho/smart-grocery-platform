# Project overview

Related: [Documentation map](README.md) ·
[Comparability audit](comparability_audit.md) ·
[Weekly basket results](weekly_basket_results.md) ·
[Classifier experiments](product_classifier_experiments.md) ·
[ADR 0006](adr/0006-main-category-classifier.md) ·
[Remote database](remote_database_architecture.md)

Smart Grocery Platform compares **official** prices from Shufersal,
Rami Levy, and Victory so a shopper can see where the **same product**
is cheaper, where a **category** is cheaper, and what an **illustrative
weekly basket** costs.

It is a **data analytics** project. Infrastructure (ETL, PostgreSQL, a
small remote analytical database) is there to make the numbers
rebuildable and reviewable.

---

## Scope

| Layer | What it is |
|---|---|
| Sources | PriceFull, Stores, PromoFull for three chains |
| Local database | Full history, staging, promotions, rebuilds |
| Analytical tables | `chain_prices` (median per chain) and `price_comparison` |
| Shared remote DB | ~25 MB subset for analysis and the chat service |
| Categories | SuperCompare silver labels + TF-IDF Linear SVM |
| Audit | Like-for-like check on barcode joins |
| Basket | 13 documented lines; potatoes and chicken excluded |
| Presentation | Tableau (local workbooks) and a read-only chat API |

---

## Pipeline

```text
official chain files
  → ETL (extract → parse → load)
  → local PostgreSQL history
  → chain_prices + price_comparison
  → SuperCompare labels + classifier
  → comparability audit
  → verified three-chain extract + weekly basket
  → Tableau / chat over the analytical layer
```

---

## Findings (documented snapshots)

PriceFull day used for the audit and basket: **2026-08-19**.

### Catalog

- **14,816** comparable products (at least two chains, same `item_code`).
- **6,408** appear in all three chains; **5,676** of those are
  audit-`valid` (88.6%) and are the published three-chain set.
- SuperCompare crawl: **15,616** rows, **15,230** unique barcodes
  (1 September 2026). Join to comparables: **5,718** labeled,
  **9,098** unlabeled.

### Weekly basket

Illustrative household shop (not a consumption survey):

| Chain | Total |
|---|---:|
| **Rami Levy** | **₪193.70** |
| Shufersal | ₪203.00 |
| Victory | ₪210.00 |

Rami Levy is **₪16.30** (7.76%) below Victory. Line-level table:
[weekly_basket_results.md](weekly_basket_results.md).

### Classifier

12 SuperCompare main categories, `item_name` + `manufacture_name`,
stratified 70/15/15:

| Metric | Test (uncorrected labels) |
|---|---|
| Accuracy | 0.871 |
| Macro F1 | 0.862 |

Manufacturer is kept as a feature. A 13-row manual overlay corrects
obvious SuperCompare errors; cigarettes stay on the analysis denylist.
A Hebrew transformer was explored as a tokenizer experiment, not as
the production model.

---

## Analytical tables

### `grocery.chain_prices`

One row per `item_code` + `chain_id`: median store price for that
chain (positive prices only). Median is used because stores inside a
chain disagree.

### `grocery.price_comparison`

One row per comparable product: Shufersal, Rami Levy, and Victory
medians, cheapest price, and cheapest chain. Ties are labeled as ties.

### Published three-chain extract

A barcode in three chains is not automatically a like-for-like SKU.

- View: `grocery.v_price_comparison_with_categories`
- Keep `include_in_analysis = true` and `chains_compared = 3`
- Keep `proposed_status = valid` from `comparability_audit.csv`
- **5,676 / 6,408** (88.6%)
- Out: 696 `needs_review`, 35 `invalid`, 1 `uncertain`
- Source prices are not capped or rewritten
- Valid large spreads stay (a high percent is not a collision by itself)

File: `data/processed/tableau_verified_three_chains.csv` (gitignored).

---

## Why categories exist

Barcode match answers “which chain is cheaper for this SKU?”
Categories answer grouping questions (dairy vs snacks vs household)
without pretending every unlabeled leftover is gold.

Labels come from **which SuperCompare subcategory endpoint** returned
the barcode. They are silver, not ground truth. Details:
[supercompare_labeling.md](supercompare_labeling.md).

---

## Limits (by design)

These are methodology choices, not a backlog:

- Comparisons use **exact `item_code`** unless a basket line is an
  approved exception (eggs) or an approved fresh-PLU triple.
- Fresh chicken and ordinary white potatoes are **out** of the money
  basket (kashrut/cut/plant and Victory potato assortment).
- Unlabeled comparables (**9,098**) are not scored into the published
  dashboard extract as if they were SuperCompare gold.
- `grocery.product_classification` is the intended home for accepted
  labels; analysis also uses crawl CSVs and SQL views documented in
  `sql/analysis/`.
- Tableau files are **local** and gitignored; GitHub holds methods,
  SQL, and write-ups.
- The chat service is **read-only** over the analytical database. It
  cannot invent SQL.

---

## How to read the rest

| Topic | Document |
|---|---|
| Install and run ETL | [getting-started.md](getting-started.md) |
| ETL design | [etl_pipeline.md](etl_pipeline.md) |
| Two databases | [remote_database_architecture.md](remote_database_architecture.md) |
| Labels | [supercompare_labeling.md](supercompare_labeling.md) |
| SVM experiments | [product_classifier_experiments.md](product_classifier_experiments.md) |
| SKU audit | [comparability_audit.md](comparability_audit.md) |
| Basket | [weekly_basket_results.md](weekly_basket_results.md) |
| Chat | [agent_platform.md](agent_platform.md) |
| Decisions | ADRs 0001–0007 |
