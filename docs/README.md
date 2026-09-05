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
| To contribute code in this repo’s style | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| To see why Pipeline / three chains / Supabase / labels | ADRs 0001–0005 below |

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
