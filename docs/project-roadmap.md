# Smart Grocery Platform — Current Status and Analysis Roadmap

Related: [Documentation map](README.md) ·
[SuperCompare labeling](supercompare_labeling.md) ·
[Remote database](remote_database_architecture.md)

## Project Goal

The Smart Grocery Platform is a data analytics portfolio project analyzing grocery prices across three Israeli supermarket chains:

- Shufersal
- Rami Levy
- Victory

The main business goal is to determine how supermarket prices differ across chains and help consumers understand where they can save money.

The project is intended primarily as a **Data Analyst portfolio project**, not as a Data Engineering project.

Therefore, the next development phases should prioritize:

1. product categorization,
2. data analysis,
3. business insights,
4. visualization,
5. communication of results.

Avoid adding unnecessary infrastructure unless it is required to complete the analysis.

---

# Current Project Status

## 1. Data Extraction and ETL — COMPLETE

Data has been collected from Shufersal, Rami Levy, and Victory.

The local PostgreSQL database contains the detailed/raw and historical data required by the ETL pipeline.

The local database should remain the main environment for:

- raw data
- historical price data
- ETL processing
- rebuilding analytical tables
- data validation

---

## 2. Database Design — COMPLETE

The project has a structured PostgreSQL data model containing product, store, price, promotion, and analytical data.

The analytical layer contains the main tables required for further analysis.

---

## 3. Cross-Chain Product Comparison — COMPLETE

Products that appear across supermarket chains have been identified using `item_code`.

A chain-level representative price is calculated using the median price across stores.

The main analytical tables include:

### `grocery.chain_prices`

One row per:

`item_code + chain_id`

Contains the median price of the product within that supermarket chain.

### `grocery.price_comparison`

One row per comparable product.

Contains:

- Shufersal price
- Rami Levy price
- Victory price
- cheapest price
- cheapest chain

This allows exact-product price comparisons across chains.

---

## 4. Shared Remote Database — COMPLETE

A shared PostgreSQL database has been created in Supabase.

The remote database contains the lightweight analytical layer rather than the complete local historical database.

Current shared tables:

- `grocery.products`
- `grocery.stores`
- `grocery.product_classification`
- `grocery.chain_prices`
- `grocery.price_comparison`

A dedicated PostgreSQL `contributor` role has been created.

The contributor has read/write access to the shared `grocery` schema.

Remote connectivity has been successfully tested through:

- PostgreSQL / psql
- pgAdmin
- Python using `get_remote_connection()`

Database credentials are stored in `.env` and must never be committed to Git.

---

# Current Phase: Product Categorization

This is the next major project phase.

The purpose of categorization is NOT to turn the project into an ML project.
Categorization exists so analysis can ask category-level questions:

> Which supermarket is cheapest for dairy?
> Is one chain consistently cheaper for snacks?
> Does the cheapest supermarket depend on the product category?

Exact barcode matching already answers “which chain is cheapest for this
exact product?” Categories unlock grouping.

### What is already done

- SuperCompare taxonomy discovered (12 parent categories, 55 subcategories).
- Full catalog crawled into
  `data/processed/supercompare_products.csv`
  (**15,616** rows, **15,230** unique barcodes, 1 September 2026).
- Earlier Dairy & Eggs barcode join against `grocery.products` was
  validated (Milk 88%, Cheese 94%, Eggs 43%).
- Resilient crawler with checkpoints and retries ([ADR 0005](adr/0005-resilient-supercompare-crawler.md)).

Details: [supercompare_labeling.md](supercompare_labeling.md).
Sample-size targets: [ADR 0004](adr/0004-product-categorization-and-training-sample.md).

### What is not done yet

- Join the **full** CSV to the **~14.8k comparable** products
  (`grocery.price_comparison`), not only the full `grocery.products`
  catalog.
- Review conflicts, weak slices, and silver-label quality.
- Write accepted labels to remote `grocery.product_classification`
  (that table is still empty).
- Train a model only for products that still have no reliable label.

Classification results belong in remote `grocery.product_classification`
so both contributors share the same labels.

---

# Next Steps

## Step 1 — Complete Product Categorization

Finish the labeling workflow. The SuperCompare crawl itself is done.

Remaining work:

1. Join `data/processed/supercompare_products.csv` to remote comparable
   products (`grocery.price_comparison.item_code`).
2. Measure coverage overall and per SuperCompare category/subcategory
   on that comparable set.
3. Review weak slices and any duplicate barcodes.
4. Store accepted mappings in remote `grocery.product_classification`.
5. Only then consider a simple model for leftovers.

Do not over-engineer the ML solution. Reliable categories that are good
enough for analytical use are the goal.

---

## Step 2 — Validate Classification Quality

Before using categories for business analysis, validate them.

Check:

- number of classified products
- number of unclassified products
- category distribution
- subcategory distribution
- obviously incorrect classifications
- categories with very few products
- products assigned to inappropriate categories

Take samples from each major category and manually inspect them.

The purpose is to ensure classification errors do not distort the later price analysis.

---

## Step 3 — Prepare the Analysis Dataset

Create a clean analytical dataset combining:

- product information
- product category
- product subcategory
- chain-level prices
- cheapest chain

The exact implementation can be a SQL view or another appropriate analytical layer.

Avoid duplicating data unnecessarily.

The resulting dataset should make business-analysis queries simple.

---

## Step 4 — Exploratory Data Analysis

Understand the dataset before answering business questions.

Investigate:

- number of comparable products
- products available in 2 chains vs 3 chains
- products per category
- price distributions
- missing prices
- extreme prices / possible outliers
- price differences between chains
- category coverage by chain

The goal is to understand limitations and biases in the comparison dataset.

---

## Step 5 — Core Business Analysis

This is one of the most important stages of the entire project.

Focus on a small number of strong business questions rather than producing many unrelated SQL queries.

Priority questions include:

### Which chain is cheapest most often?

Calculate how frequently:

- Shufersal
- Rami Levy
- Victory

has the lowest price for comparable products.

Handle ties explicitly.

### How large are price differences between chains?

Do not only identify the cheapest chain.

Measure the magnitude of the difference.

For example:

- absolute price difference
- percentage price difference
- median savings
- distribution of savings

### Which chain is cheapest by category?

Compare supermarket competitiveness across categories.

Examples:

- Dairy & Eggs
- Snacks & Sweets
- Beverages
- Frozen Food
- Personal Care
- Cleaning

Determine whether different chains are competitive in different categories.

### Are the conclusions different for products available in all three chains?

Separate:

- products available in exactly two chains
- products available in all three chains

This prevents availability differences from creating misleading conclusions.

---

## Step 6 — Basket Analysis

Move from individual products to a consumer-oriented question:

> What happens when someone buys an entire grocery basket?

Create several representative baskets where supported by the data.

For each basket calculate:

- Shufersal total
- Rami Levy total
- Victory total
- cheapest chain
- absolute savings
- percentage savings

Basket assumptions must be documented clearly.

Do not force comparisons when equivalent/comparable products are unavailable.

---

## Step 7 — Visualization / Dashboard

After the analytical questions and metrics are stable, create the presentation layer.

The dashboard should communicate insights rather than simply display tables.

Potential views include:

- cheapest chain overall
- cheapest chain by category
- median price differences
- potential savings
- basket comparison
- product-level comparison
- filters for category/subcategory

Do not build the dashboard before the analytical logic is validated.

---

## Step 8 — Insights and Recommendations

Translate analytical results into understandable conclusions.

Examples of the type of conclusions the project should eventually support:

- which chain wins most exact-product comparisons
- whether that advantage is large or small
- which categories each chain performs best in
- whether consumers can achieve meaningful savings
- whether one supermarket is consistently cheapest or whether the answer depends on the shopping basket

Every final claim must be supported by the data.

Document important analytical limitations.

---

## Step 9 — Portfolio Presentation

Once analysis is complete, prepare the project for GitHub and CV presentation.

The final project story should emphasize:

**Business problem → Data → Methodology → Analysis → Insights → Visualization**

Do not make infrastructure the main story.

ETL, PostgreSQL, Supabase, remote collaboration, permissions, and database architecture demonstrate technical ability, but they support the analysis rather than being the final product.

The portfolio should highlight measurable findings such as:

- number of products analyzed
- number of comparable products
- price differences
- category-level findings
- potential savings

Only use numbers actually produced by the final analysis.

---

# Development Principle

This is primarily a **Data Analyst portfolio project**.

When suggesting future work, prioritize:

1. analytical correctness
2. SQL and Python analysis
3. data validation
4. business questions
5. visualization
6. interpretation and communication

Do NOT introduce additional architecture, cloud services, abstractions, frameworks, or engineering complexity unless there is a concrete analytical requirement for them.

The infrastructure is currently sufficient to proceed with the analysis.

---

# AI-Assisted Development

The project is being developed with significant assistance from ChatGPT and Cursor.

AI may help with:

- writing code
- SQL
- debugging
- documentation
- architecture suggestions
- refactoring

However, code should remain understandable to the project owner.

When generating or modifying important analytical logic:

- explain what the code does
- explain why the approach is being used
- avoid unnecessary complexity
- prefer solutions appropriate for a junior Data Analyst project
- make assumptions explicit
- do not silently introduce major architectural changes

The goal is not simply to generate working code, but to maintain a project whose analytical reasoning can be explained and defended in a technical interview.
