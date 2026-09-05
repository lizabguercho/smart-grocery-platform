# 🛒 Smart Grocery Platform

## Overview

Smart Grocery Platform is a data-analyst portfolio project. It compares
grocery prices across three Israeli supermarket chains — **Shufersal**,
**Rami Levy**, and **Victory** — so a shopper can see where the same
product is cheaper, and later where a category or a basket is cheaper.

The supporting engineering (ETL, PostgreSQL, a small shared remote
database, SuperCompare category labels) exists so that analysis can be
done carefully. It is not the final product.

**Documentation map:** [docs/README.md](docs/README.md) lists every
markdown file, what it is for, and a suggested reading order.

---

## Project Goals

- Collect official PriceFull, Stores, and PromoFull files from three chains.
- Store them in a normalized local PostgreSQL database with history.
- Publish a small analytical subset (comparable products + chain prices).
- Assign product categories so analysis can go beyond exact barcodes.
- Answer: which chain is cheapest overall, by category, and for baskets.
- Present findings (dashboard / portfolio write-up) after the analysis is stable.

---

## Getting Started

This project uses **uv** for Python environments and **PostgreSQL** for storage.

```bash
# Install dependencies into .venv (Python 3.11 via .python-version)
uv sync

# Configure database credentials
cp .env.example .env
# edit .env with your local PostgreSQL settings

# Create database + schema/tables/indexes
./install.sh

# Verify connection
uv run python scripts/check_db_connection.py

# Run Shufersal PriceFull ETL (from repo root)
uv run python -m src.etl --chain shufersal --extract prices_full --max-pages 2 --max-files 3
# Or in Cursor: Run and Debug → ETL Pipeline, then pick chain and dataset
```

Full setup: **[docs/getting-started.md](docs/getting-started.md)**.
Where we are in the work: **[docs/project-roadmap.md](docs/project-roadmap.md)**.
All docs: **[docs/README.md](docs/README.md)**.

---

## Current Features

- Unified ETL CLI (`python -m src.etl`) for Shufersal, Rami Levy, and Victory.
- Official PriceFull, Stores, and PromoFull extract → parse → load.
- Normalized local PostgreSQL (`grocery` schema) with historical prices.
- Analytical tables: `chain_prices` (median price per chain) and
  `price_comparison` (cheapest chain, including ties).
- Shared remote PostgreSQL (Supabase) with the small analytical subset.
- SuperCompare crawler for external category labels
  (`data/processed/supercompare_products.csv`).
- Data-quality checks, `.env` configuration, SQL for schema and analysis.

---

## Project Structure

```
Smart-Grocery-Platform/
├── data/                      gitignored working files
│   ├── raw/                   PriceFull, Stores, PromoFull, SuperCompare pages
│   └── processed/             supercompare_products.csv and crawl report
├── docs/                      guides + ADRs — start at docs/README.md
│   └── adr/
├── sql/
│   ├── 01–07                  local schema, tables, indexes, quality checks
│   ├── analysis/              chain_prices and price_comparison
│   └── remote/                shared database schema and grants
├── src/
│   ├── etl/                   CLI, factory, Pipeline
│   ├── data_extraction/       chain downloaders and XML parsers
│   ├── database_loader/       PostgreSQL loaders and connections
│   └── product_classification/
│       └── supercompare/      category crawler
├── scripts/                   connection check, inspection helpers
├── test/unit/
├── CONTRIBUTING.md
├── pyproject.toml
└── README.md
```

---

## Database Design

There are **two** PostgreSQL databases. Details:
[docs/remote_database_architecture.md](docs/remote_database_architecture.md).

### Local (ETL source of truth)

| Table | Role |
|---|---|
| `grocery.products` | Latest product metadata, keyed by `item_code` (barcode) |
| `grocery.product_prices` | Historical store-level prices |
| `grocery.products_staging` | Truncated each PriceFull load |
| `grocery.stores` | Latest store metadata |
| `grocery.promotions` / `promotion_groups` / `promotion_items` | PromoFull history |
| `grocery.chain_prices` | Median price per `item_code` × chain |
| `grocery.price_comparison` | One row per product in at least two chains |
| `grocery.product_classification` | Category labels (still empty until labels are promoted) |

### Remote (shared analysis, ~25 MB)

A subset of the local analytical tables, so two people can classify and
query without copying 4 GB of history.

---

## Technologies

- Python 3.11
- PostgreSQL
- SQL
- psycopg
- python-dotenv
- Requests
- BeautifulSoup
- lxml
- Pandas
- Git

---

## ETL Pipeline

Current workflow:

```
python -m src.etl --chain <chain> --extract prices_full
        ↓
Extract (chain-specific download)
        ↓
Parse (shared PriceFull XML)
        ↓
Load into PostgreSQL (staging → products → product_prices)
```

See **[docs/etl_pipeline.md](docs/etl_pipeline.md)** and
**[CONTRIBUTING.md](CONTRIBUTING.md)**.

Category labels are a separate workflow (`python -m
src.product_classification.supercompare`), documented in
**[docs/supercompare_labeling.md](docs/supercompare_labeling.md)**.
They are not part of the supermarket-file ETL.

---

## Data Quality

The project validates:

- Duplicate products
- Duplicate price records
- Missing required values
- Referential integrity
- Row counts

---

## Next (analysis, not more infrastructure)

See **[docs/project-roadmap.md](docs/project-roadmap.md)**.

1. Join SuperCompare barcodes to comparable products and store reviewed
   labels in remote `grocery.product_classification`.
2. Validate category quality.
3. Category-level price analysis, then baskets, then a dashboard.

---

## Author

Liza Benguerchon

This project was developed as part of my data analytics portfolio to demonstrate practical skills in:

- Python
- SQL
- PostgreSQL
- ETL pipelines
- Data modeling
- Data quality
- Analytics engineering