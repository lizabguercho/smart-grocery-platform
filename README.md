# 🛒 Smart Grocery Platform

## Overview

Smart Grocery Platform is an end-to-end data engineering and analytics project that collects supermarket price data from Israeli retailers, stores it in a PostgreSQL database, and enables price comparison and market analysis.

The project demonstrates the complete data pipeline, from data extraction to database design and analysis, following software engineering and data engineering best practices.

---

## Project Goals

- Build an automated ETL pipeline for Israeli supermarket price data.
- Design a normalized PostgreSQL database.
- Compare product prices across stores and over time.
- Perform data quality validation.
- Build analytical dashboards and insights.
- Develop a user interface for searching and comparing products (future phase).

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
```

Full setup details (prerequisites, PostgreSQL, ETL order, troubleshooting): **[docs/getting-started.md](docs/getting-started.md)**.

---

## Current Features

- Unified ETL CLI (`python -m src.etl`) for Shufersal, Rami Levy, and Victory.
- Download official PriceFull files per chain.
- Parse XML price files into `PriceFullProduct` records.
- Store product information in a normalized PostgreSQL database.
- Maintain historical product prices.
- Automated data quality checks.
- Environment-based database configuration.
- SQL scripts for database creation and maintenance.

---

## Project Structure

```
Smart-Grocery-Platform/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
│
├── database/
│   ├── backups/
│   └── erd/
│
├── docs/
│   └── adr/
│
├── notebooks/
│
├── scripts/
│
├── test/
│   └── unit/
│
├── sql/
│   ├── 01_create_schema.sql
│   ├── 02_create_tables.sql
│   ├── 03_load_products.sql
│   ├── 04_load_product_prices.sql
│   ├── 05_indexes.sql
│   ├── 06_views.sql
│   ├── 07_data_quality_checks.sql
│   └── inspection_queries.sql
│
├── src/
│   ├── etl/
│   ├── data_extraction/
│   └── database_loader/
│
├── CONTRIBUTING.md
├── pyproject.toml
└── README.md
```

---

## Database Design

The project uses a normalized PostgreSQL database.

### Tables

### products

Stores static product information.

Examples:

- Product name
- Manufacturer
- Unit of measure
- Package size

Each product appears only once.

---

### product_prices

Stores historical prices.

Each row represents:

- Product
- Store
- Extraction date
- Price

This allows price comparison across stores and tracking price changes over time.

---

### products_staging

Temporary staging table used during the ETL process before loading data into the production tables.

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

---

## Data Quality

The project validates:

- Duplicate products
- Duplicate price records
- Missing required values
- Referential integrity
- Row counts

---

## Future Improvements

- Implement Stores extraction (`--extract stores`).
- Scheduled automatic updates
- Product search API
- Interactive dashboard
- Price history visualizations
- Shopping basket optimization
- Web application

---

## Author

Liza Rabkina

This project was developed as part of my data analytics portfolio to demonstrate practical skills in:

- Python
- SQL
- PostgreSQL
- ETL pipelines
- Data modeling
- Data quality
- Analytics engineering