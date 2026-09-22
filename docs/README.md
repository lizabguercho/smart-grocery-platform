# Documentation map

This folder is the project’s written memory. Use it to answer “where are
we, why did we choose this, and what do I run?” without reading the
source first.

The repository README is a short overview. This page is the index of
every markdown file and the order that makes them make sense.

---

## What this project is

Smart Grocery Platform is a **data-analyst portfolio project**.

The business question is:

> Across Shufersal, Rami Levy, and Victory, where is the same grocery
> product cheaper — overall, by category, and in a typical basket?

Infrastructure (ETL, PostgreSQL, Supabase, SuperCompare crawler) exists
to make that analysis possible. It is not the final story of the
project. The intended narrative is:

```text
business problem
  → official chain price files
  → local ETL + historical database
  → small shared analytical database
  → product categories
  → SQL analysis and insights
  → visualization
```

Current phase: **product categorization**. Price comparison tables
already exist. SuperCompare silver labels have been crawled into
`data/processed/supercompare_products.csv`. Those labels are **not**
yet loaded into `grocery.product_classification`.

---

## How the documents fit together

```text
README.md                          60-second overview + install snippet
docs/README.md                     this map
        │
        ├── getting-started.md     how to set up a machine
        ├── project-roadmap.md     what is done vs what comes next
        │
        ├── etl_pipeline.md        ETL architecture (source of truth)
        ├── etl-process-flow.md    file-by-file walk of one run
        ├── client-server-architecture.md
        │                          Python client ↔ PostgreSQL
        ├── remote_database_architecture.md
        │                          local 4 GB vs remote 25 MB
        ├── supercompare_labeling.md
        │                          how category labels were obtained
        ├── product_classifier_experiments.md
        │                          12-class TF-IDF experiments (name vs manufacturer)
        ├── product_classifier_error_analysis.md
        │                          Test mistakes of the winning Linear SVM
        ├── modeling_decisions.md  short conclusions (canonical: ADR 0006)
        ├── agent_platform.md      chat service over the analytical database
        ├── comparability_audit.md barcode/SKU like-for-like review
        ├── weekly_basket_coverage.md
        │                          illustrative weekly basket vs catalog coverage
        ├── weekly_basket_results.md
        │                          13-line comparable basket totals
        │
        └── adr/                   durable decisions (do not rewrite history)
```

**Guides** describe how the system works today. **ADRs** record *why* a
choice was made and what was rejected. If a guide and an ADR disagree
on current status, trust the guide for “what exists now” and the ADR
for “why we chose it” — then update the ADR with a dated note rather
than silently changing the original decision.

---

## Suggested reading order

| If you want… | Read this |
|---|---|
| To clone, install, connect, and run ETL | [getting-started.md](getting-started.md) |
| To know what phase we are in | [project-roadmap.md](project-roadmap.md) |
| To understand extract → parse → load | [etl_pipeline.md](etl_pipeline.md) |
| To follow one command through the files | [etl-process-flow.md](etl-process-flow.md) |
| To understand local vs remote databases | [remote_database_architecture.md](remote_database_architecture.md) |
| To understand SuperCompare labels and the CSV | [supercompare_labeling.md](supercompare_labeling.md) |
| To understand the 12-class classifier experiments | [product_classifier_experiments.md](product_classifier_experiments.md) |
| To see which model and features we kept | [ADR 0006](adr/0006-main-category-classifier.md) |
| To ask the data questions in plain language | [agent_platform.md](agent_platform.md) |
| To see which barcodes are not like-for-like | [comparability_audit.md](comparability_audit.md) |
| To see which weekly-basket staples have like-for-like codes | [weekly_basket_coverage.md](weekly_basket_coverage.md) |
| To see the comparable weekly-basket totals | [weekly_basket_results.md](weekly_basket_results.md) |
| To contribute code in this repo’s style | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| To see why Pipeline / three chains / Supabase / labels / classifier / chat | ADRs 0001–0007 below |

---

## Guides (what exists today)

### [getting-started.md](getting-started.md)

Local setup: `uv`, Python 3.11, PostgreSQL, `.env`, `./install.sh`,
unit tests, and ETL commands.

It also documents **remote contributor access** (Supabase session
pooler). Use `DB_*` for the local ETL database and `REMOTE_DB_*` for
the shared analytical database. Do not point the ETL at the remote
contributor role.

### [project-roadmap.md](project-roadmap.md)

Status and next analysis steps. Treat this as the product plan:

1. ETL — complete
2. Database model — complete
3. Cross-chain `chain_prices` / `price_comparison` — complete
4. Shared remote database — complete
5. **Product categorization — in progress** (crawl done, labels not in DB)
6. Then: validate labels → analysis dataset → EDA → business questions
   → baskets → dashboard → portfolio write-up

### [etl_pipeline.md](etl_pipeline.md)

Canonical ETL document. Covers:

- one CLI: `python -m src.etl --chain … --extract …`
- Strategy + Factory + Pipeline
- how Shufersal (HTTP), Rami Levy (FTP), and Victory (API) differ
- PriceFull staging → `products` → `product_prices`
- PromoFull → `promotions` / `promotion_groups` / `promotion_items`
- keys, validation, and known gaps (PromoFull item codes missing from
  PriceFull)

### [etl-process-flow.md](etl-process-flow.md)

A walkthrough of one run at file level (CLI → factory → extractor →
parser → loader). Useful when you need to open the right Python module.
Architecture rules still live in `etl_pipeline.md`.

### [client-server-architecture.md](client-server-architecture.md)

How Python talks to PostgreSQL: connector module, `.env`, transactions,
parameterized queries, local vs hosted server. This is the *connection*
story, not the table design.

Code lives in `src/database_loader/connection.py`
(`get_connection()` local, `get_remote_connection()` remote).

### [remote_database_architecture.md](remote_database_architecture.md)

Why the project has two databases:

| Layer | Size (approx.) | Holds |
|---|---|---|
| Local PostgreSQL | 4.1 GB | Full history, staging, promotions, ETL |
| Remote Supabase PostgreSQL | 25 MB | Shared analysis tables only |

Shared tables: `products`, `stores`, `product_classification`,
`chain_prices`, `price_comparison`.

The remote database is **not** the source of truth for supermarket
files. Rebuild analytical tables locally, then sync.

### [supercompare_labeling.md](supercompare_labeling.md)

How category labels were collected from SuperCompare:

- category HTML for taxonomy, product API for barcodes
- labels come from **which subcategory endpoint** returned the row
- join to our catalog is exact `item_code` / barcode equality
- labels are **silver / external**, not ground truth
- full-taxonomy crawl output:
  `data/processed/supercompare_products.csv`
- comparable join + category distribution: sections 9b–9d of this file,
  and `data/processed/price_comparison_with_categories.csv`

Related code: `src/product_classification/`.

### [product_classifier_experiments.md](product_classifier_experiments.md)

First classical ML pass on the **5,718** labeled comparable products:
`item_name` vs `item_name` + `manufacture_name`, three TF-IDF models,
stratified 70/15/15 split. Winner is chosen on validation Macro F1.
The durable choice of features and model is
[ADR 0006](adr/0006-main-category-classifier.md).
Test mistakes: [product_classifier_error_analysis.md](product_classifier_error_analysis.md).

### [agent_platform.md](agent_platform.md)

The chat service that makes the analytical layer answerable in plain language:

- `uv run python -m src.agent_platform`, served with FastAPI over SSE
- a pydantic-ai agent combining `SKILL.md` playbooks with five read-only SQL
  tools; no free-form SQL, and the connection is read-only server-side
- explicit context control, so what the model was sent is always inspectable
- reads the **remote** analytical database (`REMOTE_DB_*`), never the local ETL
  database

The durable choices are [ADR 0007](adr/0007-agent-platform-chat-service.md).
Related code: `src/agent_platform/`.

### [comparability_audit.md](comparability_audit.md)

Read-only check of whether `item_code` is the same sellable SKU across
chains. Uses 2026-08-19 PriceFull names, quantities, and manufacturers,
not the single `grocery.products` row. Includes the 70-product ≥100%
review and scores the rest of the eligible catalog. Manufacturer
conflict alone is not invalid. Conservative Tableau publishing keeps
only audit-valid three-chain rows
(`data/processed/tableau_verified_three_chains.csv`, 5,676 of 6,408).
The full audit CSV and the original Tableau extract are unchanged.

### [weekly_basket_coverage.md](weekly_basket_coverage.md)

Illustrative 13-item weekly basket (milk, eggs, bread, chicken, rice,
pasta, potatoes, produce, yogurt, household). Read-only coverage
against the verified three-chain extract, the broader comparison
tables, store-level prices, and PriceFull. Packaged staples match on
barcode; fresh produce and chicken mostly use chain-specific weighted
PLUs and need a separate matching table.

### [weekly_basket_results.md](weekly_basket_results.md)

13-line illustrative comparable basket (packaged verified SKUs, approved
fresh PLUs, basket-only eggs). Potatoes and chicken excluded. Rami Levy
₪193.70 vs Victory ₪210.00. Tableau CSV:
`data/processed/weekly_basket_comparison.csv`.

---

## Architecture Decision Records (`docs/adr/`)

ADRs are numbered, accepted decisions. They stay even after the
implementation catches up. Add a short “Later update” section when
reality changes; do not pretend the original context never existed.

| ADR | Decision | Read when you need to know… |
|---|---|---|
| [0001](adr/0001-etl-pipeline-orchestration.md) | One `Pipeline` object, Strategy + Factory | Why there is not a `process_*.py` per chain |
| [0002](adr/0002-three-chains-and-extraction.md) | Exactly Shufersal, Rami Levy, Victory; official files only | Why not every Israeli chain, and why not scrape storefronts |
| [0003](adr/0003-remote-analytical-database.md) | Local full DB + small remote analytical DB | Why Supabase and which tables are shared |
| [0004](adr/0004-product-categorization-and-training-sample.md) | Categorize comparable products; SuperCompare silver labels first | Sample sizes, coverage, what not to train on |
| [0005](adr/0005-resilient-supercompare-crawler.md) | Checkpointed, retrying SuperCompare crawler | Why pages are saved under `data/raw/supercompare/` |
| [0006](adr/0006-main-category-classifier.md) | TF-IDF + Linear SVM; keep manufacturer; 12 main categories | Why this classical model, split, and metric |
| [0007](adr/0007-agent-platform-chat-service.md) | Streaming chat service; skills as docs, fixed read-only SQL as capability | Why no text-to-SQL, how ties are counted, how context is controlled |

---

## Data artifacts the docs refer to

These files are **gitignored** (large / regenerated). They are the
working data the markdown describes.

| Path | What it is |
|---|---|
| `data/raw/price_full/<chain>/` | Official PriceFull dumps |
| `data/raw/stores/<chain>/` | Official Stores dumps |
| `data/raw/promo_full/<chain>/` | Official PromoFull dumps |
| `data/raw/supercompare/` | Checkpointed SuperCompare API pages + `taxonomy.json` |
| `data/processed/supercompare_products.csv` | Full crawl export: barcode + SuperCompare category path |
| `data/processed/supercompare_crawl_report.json` | Crawl completeness report |
| `data/processed/price_spread_100pct_review.csv` | Manual review of 70 eligible products with ≥100% spread |
| `data/processed/comparability_audit.csv` | Full eligible-catalog comparability audit (14,653 rows) |
| `data/processed/tableau_price_comparison.csv` | Full Tableau extract from `v_price_comparison_with_categories` |
| `data/processed/tableau_verified_three_chains.csv` | Conservative three-chain dashboard extract (5,676 audit-valid products) |
| `data/processed/weekly_basket_candidates.csv` | Candidate barcodes for the illustrative weekly basket (coverage only) |
| `data/processed/weekly_basket_fresh_matches.csv` | Pending per-chain fresh SKU matches (cucumbers, tomatoes, potatoes, bananas, chicken), ₪/kg |
| `data/processed/weekly_basket_exceptions.csv` | Basket-only SKU exceptions (does not change the comparability audit) |
| `data/processed/weekly_basket_comparison.csv` | 13-line comparable weekly basket (39 chain rows) for Tableau |

SQL that *is* in Git:

| Path | What it is |
|---|---|
| `sql/01`–`07` | Schema, tables, indexes, quality checks |
| `sql/analysis/` | Builds `chain_prices` and `price_comparison` |
| `sql/remote/` | Remote schema, grants, and load helpers |

---

## Conventions for editing these docs

- Put **how to run** in getting-started / etl_pipeline, not in every ADR.
- Put **why** in an ADR when the choice should survive a rewrite.
- Put **current phase and next steps** in the roadmap; keep checklists
  there, not duplicated in three places.
- When numbers change (row counts, match rates, crawl size), update
  `supercompare_labeling.md` and ADR 0004 together.
- Never put database passwords in markdown. Variable names only.
