# 0004. Product categorization and training sample

## Status

Accepted for the decision to categorize products.

SuperCompare barcode coverage below is a **partial-crawl** snapshot
against the full `grocery.products` catalog. A complete taxonomy crawl
finished on 1 September 2026
(`data/processed/supercompare_products.csv`: 15,616 rows, 15,230 unique
barcodes, 12 parents, 55 subcategories). Match rates have **not** yet
been recomputed on that full file, and they have **not** yet been
restricted to the ~14.8k comparable products. Update this table when
that join exists. Catalog counts: [supercompare_labeling.md](../supercompare_labeling.md).

## Context

Exact barcode matching already answers:

> Which supermarket is cheapest for this exact product?

It cannot answer:

> Which supermarket is cheapest for dairy?
> Is one chain cheaper for snacks than for produce?

Those questions need a **category** and **subcategory** on each
product. Names and manufacturers are not a grocery taxonomy.

Categorization is done on the **remote** database, on the products used
for analysis: about **14,800** comparable products
(`grocery.price_comparison` — the same `item_code` in at least two
chains). That is the set that answers “which chain is cheapest?”.

The local catalog is larger (tens of thousands of products, including
items that appear in only one chain). Those extra rows are not the
classification scope. Labeling even the 14k remote products by hand is
not realistic.

The project is a Data Analyst portfolio. Categorization exists to unlock
analysis, not to become an ML research project. Labels must be good
enough that category-level price comparisons are not dominated by
misclassified junk.

The working taxonomy is **SuperCompare’s** parent categories and
subcategories (discovered by the crawler). Labels are
**external/silver**, joined on barcode — not guaranteed ground truth.
See [supercompare_labeling.md](../supercompare_labeling.md).

Results are stored in `grocery.product_classification` on the **remote**
database so both contributors share the same labels
([ADR 0003](0003-remote-analytical-database.md)).

## Decision

### Why categorize

Assign `category` + `subcategory` so analysis can group `chain_prices`
and `price_comparison` by product type.

Do **not** over-build the model. SuperCompare silver labels plus a
simple classifier for unlabeled leftovers is enough if quality checks
pass.

### How labels are obtained

Preferred order:

1. **SuperCompare silver labels** for barcodes that match the remote
   comparable products (membership in a subcategory endpoint).
2. **Manual review** of a stratified sample to estimate silver-label
   error and to cover weak SuperCompare slices.
3. **A trained model** to predict remaining products that have no
   reliable external label.

A separate project taxonomy file and keyword-rule classifier were
removed. SuperCompare names are the labels used for now.

### How much sample to use (working target)

The remote set is ~14.8k comparable products. SuperCompare currently
supplies the parent/subcategory names in the coverage table below.
A useful model needs **balanced coverage**, not a huge random dump of
one category.

| Level | Working target | Why |
|-------|----------------|-----|
| Per main category | **at least ~100–200** labeled products | Simple text models (for example TF-IDF + linear classifier) need dozens to a few hundred examples per class. Below ~100, rare categories collapse into “Other”. |
| Per subcategory we will report in analysis | **at least ~50–100** where possible | Many SuperCompare subcategories are sparse (Eggs, Dips & Spreads). Report at subcategory only where the sample supports it. |
| Overall labeled set to train on | **about 2,000–5,000** products | Roughly 15–35% of the 14k remote products. Enough for train/validation/test without labeling the entire remote set. SuperCompare silver labels can supply much of this. |
| Manual quality sample | **about 30–50 per main category** (on top of silver labels) | Checks whether SuperCompare/model labels are safe for price analysis. |
| Split | **train / validation / test** (for example 70/15/15) on the labeled set | Test set is not used to pick rules or hyperparameters. |

These numbers are **starting targets**, not a proven optimum.

### SuperCompare coverage (measured)

Barcode join of SuperCompare subcategory endpoints to
`grocery.products`. **Matched** = SuperCompare `itemCode` present in
our catalog. **Coverage** = Matched / SuperCompare Total.

Status bands used here: 🟢 High ≥ 80%, 🟡 Medium 60–80%, 🔴 Low < 60%.

| Main Category | Subcategory | Matched | SuperCompare Total | Coverage | Status |
|---|---|---:|---:|---:|---|
| **Baby** | Baby Care | 117 | 142 | **82.4%** | 🟢 High |
| | Baby Food | 103 | 141 | **73.0%** | 🟡 Medium |
| | Diapers | 30 | 34 | **88.2%** | 🟢 High |
| **Bakery** | Bread | 153 | 222 | **68.9%** | 🟡 Medium |
| | Cookies & Cakes | 483 | 604 | **80.0%** | 🟢 High |
| | Pastries | 35 | 55 | **63.6%** | 🟡 Medium |
| **Beverages** | Alcohol | 293 | 433 | **67.7%** | 🟡 Medium |
| | Hot Drinks | 222 | 286 | **77.6%** | 🟡 Medium |
| | Juices | 143 | 162 | **88.3%** | 🟢 High |
| | Soft Drinks | 86 | 105 | **81.9%** | 🟢 High |
| | Water | 46 | 59 | **78.0%** | 🟡 Medium |
| **Dairy & Eggs** | Cheese | 296 | 315 | **94.0%** | 🟢 High |
| | Cream & Butter | 68 | 72 | **94.4%** | 🟢 High |
| | Eggs | 6 | 14 | **42.9%** | 🔴 Low |
| | Milk | 88 | 100 | **88.0%** | 🟢 High |
| | Yogurt & Pudding | 227 | 255 | **89.0%** | 🟢 High |
| **Deli & Salads** | Dips & Spreads | 4 | 8 | **50.0%** | 🔴 Low |
| | Hummus & Tahini | 99 | 115 | **86.1%** | 🟢 High |
| | Packaged Salads | 24 | 29 | **82.8%** | 🟢 High |
| | Prepared Foods | 25 | 30 | **83.3%** | 🟢 High |
| **Fresh Produce** | Fresh Fruit | 221 | 474 | **46.6%** | 🔴 Low |
| | Fresh Herbs | 117 | 157 | **74.5%** | 🟡 Medium |
| | Fresh Vegetables | 409 | 684 | **59.8%** | 🔴 Low |
| **Frozen** | Frozen Meals | 111 | 129 | **86.0%** | 🟢 High |
| | Frozen Meat & Poultry | 55 | 75 | **73.3%** | 🟡 Medium |
| | Frozen Pastry & Pizza | 131 | 167 | **78.4%** | 🟡 Medium |
| | Frozen Vegetables & Fruit | 116 | 164 | **70.7%** | 🟡 Medium |
| | Ice Cream & Desserts | 178 | 190 | **93.7%** | 🟢 High |
| **Household & Cleaning** | Cleaning Products | 808 | 995 | **81.2%** | 🟢 High |
| | Disposable Tableware | 112 | 211 | **53.1%** | 🔴 Low |
| | Laundry | 100 | 114 | **87.7%** | 🟢 High |
| | Paper Products | 90 | 135 | **66.7%** | 🟡 Medium |
| | Pet Food & Supplies | 55 | 69 | **79.7%** | 🟡 Medium |
| | Trash Bags & Wraps | 302 | 511 | **59.1%** | 🔴 Low |
| **Meat & Fish** | Beef & Lamb | 176 | 354 | **49.7%** | 🔴 Low |
| | Deli & Processed Meat | 171 | 186 | **91.9%** | 🟢 High |
| | Fish & Seafood | 169 | 275 | **61.5%** | 🟡 Medium |
| | Poultry | 138 | 210 | **65.7%** | 🟡 Medium |

Across this snapshot: **6,007** matched barcodes out of **8,281**
SuperCompare products (**72.5%**). Many subcategories already meet the
~100–200 labeled-example target from silver labels alone (for example
Cheese, Cleaning Products, Cookies & Cakes, Fresh Vegetables).

Weak joins (🔴) should not be used as the only training source for that
slice: Eggs, Dips & Spreads, Fresh Fruit, Fresh Vegetables, Disposable
Tableware, Trash Bags & Wraps, Beef & Lamb. Fresh Vegetables has many
matched rows (409) but low coverage, so volume is high and
representativeness is still a risk.

This table **is** the working taxonomy (SuperCompare parent +
subcategory) for the slices that had been crawled when match rates were
measured. The later full crawl also includes **Pantry & Cooking**,
**Snacks & Sweets**, and **Personal Care & Hygiene**. Those three
parents now dominate the CSV by row count; they still need a barcode
join against comparable products before they can be used as training
or analysis coverage.

Do **not** train a classifier on Dairy & Eggs alone and apply it to all
~14k comparable products.

### How to sample

- Draw the sample from `price_comparison` (about 14.8k `item_code`
  values present in two or more chains). That is the classification
  universe.
- Stratify by SuperCompare category, not by a uniform random 1% of
  rows.
- Keep non-food SuperCompare slices (household, baby, pet) separate
  from food-category price stats.
- Measure coverage: classified vs unclassified, distribution by
  category, and conflicts when one barcode appears in two SuperCompare
  endpoints.

## Rejected alternatives

- **No categories.** The roadmap’s category-level questions cannot be
  answered.
- **Manually label all ~14k comparable products.** Time cost is too
  high for the analysis payoff. One-chain local catalog rows are out
  of scope.
- **Keyword rules only.** A small rule file was started and deleted.
  Hebrew product strings vary too much across chains for that to be
  the main system.
- **Treat SuperCompare as ground truth with no review.** Silver labels;
  `categoryConfidence` includes `ai` / `keyword` / `manual`.
- **Deep learning or an LLM on every product as the first approach.**
  Over-engineering for this project. A linear model or even
  SuperCompare-only labels may already be enough for analysis.
- **Train on a single subcategory (Milk) and generalize.** The Milk
  test was a join check, not a training set.

## Consequences

- Classification quality gates the later EDA and “cheapest chain by
  category” charts. A bad Eggs classifier would distort that slice.
- The SuperCompare **crawl** is complete. Remaining work is the join,
  quality review, and promotion into `product_classification`. Match
  rates and label issues belong in `docs/supercompare_labeling.md`.
- Update **this ADR** when:

  1. coverage is recomputed on the ~14.8k comparable products (not the
     full `grocery.products` catalog),
  2. a labeled train/validation/test split actually exists,
  3. the working sample targets above are confirmed or replaced by
     measured needs.

- Store accepted labels in remote `grocery.product_classification`,
  not only in local notebooks.
