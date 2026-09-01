# Getting Started

This guide covers setting up a local development environment for Smart Grocery Platform using **uv**, **Python 3.11**, and **PostgreSQL**. Contributors who only need the shared analytical dataset can connect to the remote database instead of installing a full local copy.

All other markdown files are indexed in **[docs/README.md](README.md)**.

## Prerequisites

Install these before continuing:

| Tool | Notes |
|------|--------|
| [uv](https://docs.astral.sh/uv/) | Fast Python package manager (uses `pyproject.toml` + `uv.lock`) |
| [PostgreSQL](https://www.postgresql.org/download/) | Local server for the grocery schema |
| Git | Clone and version control |

Optional but recommended:

- `psql` (comes with PostgreSQL) to run SQL scripts from the terminal

### Install uv (if needed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Confirm:

```bash
uv --version
```

---

## 1. Clone the repository

```bash
git clone <repository-url>
cd smart-grocery-platform
```

---

## 2. Create the Python environment

The project pins Python via `.python-version` (`3.11`) and locks dependencies in `uv.lock`.

From the repo root:

```bash
# Install Python 3.11 if uv does not already have it
uv python install 3.11

# Create .venv and install dependencies exactly as locked
uv sync
```

This creates a `.venv/` directory and installs everything listed in `pyproject.toml` (resolved from `uv.lock`).

### Activate the virtual environment (optional)

Most commands can use `uv run` without activating. To activate manually:

```bash
# macOS / Linux
source .venv/bin/activate
```

---

## 3. Configure environment variables

Database credentials are loaded from a `.env` file in the project root (see `src/database_loader/connection.py`).

Copy the example file and edit values to match your local PostgreSQL setup:

```bash
cp .env.example .env
```

Example contents:

```env
# Local ETL database (source of truth for supermarket files)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=smart_grocery
DB_USER=postgres
DB_PASSWORD=your_password_here

# Shared analytical database (Supabase). Leave blank if you only work locally.
REMOTE_DB_HOST=
REMOTE_DB_PORT=5432
REMOTE_DB_NAME=postgres
REMOTE_DB_USER=
REMOTE_DB_PASSWORD=
```

`.env` is gitignored — never commit real credentials.

Python uses `get_connection()` for `DB_*` and `get_remote_connection()`
for `REMOTE_DB_*` (`src/database_loader/connection.py`). Keep them
separate: the ETL writes staging and history that do not belong on the
remote contributor database.

---

## 4. Set up PostgreSQL

### Create the database, schema, tables, and indexes

With `.env` configured and a PostgreSQL **server** running:

```bash
./install.sh
```

If `psql` is missing, the script installs the client tools automatically (`brew install libpq` on macOS, or the distro package on Linux). You still need a running PostgreSQL server (local or remote) that matches your `.env` settings.

This creates the database named in `DB_NAME` (if needed) and applies:

- `sql/01_create_schema.sql`
- `sql/02_create_tables.sql`
- `sql/05_indexes.sql`

Or run the same steps manually with `psql` from the repo root.

What each file does:

| Script | Purpose |
|--------|---------|
| `01_create_schema.sql` | Creates the `grocery` schema |
| `02_create_tables.sql` | Products, prices, staging, stores, promotions, classification |
| `03_load_products.sql` | Loads products from staging (after you load staging data) |
| `04_load_product_prices.sql` | Loads prices from staging |
| `05_indexes.sql` | Indexes on prices and promotions |
| `06_views.sql` | Analytical views |
| `07_data_quality_checks.sql` | Validation queries |
| `inspection_queries.sql` | Ad-hoc inspection queries |
| `sql/analysis/` | Builds `chain_prices` and `price_comparison` |
| `sql/remote/` | Remote schema, grants, and data helpers |

---

## Remote Database Access

The project uses a shared Supabase PostgreSQL database for collaborative
analysis. See
**[docs/remote_database_architecture.md](remote_database_architecture.md)**
for which tables are shared and why.

Contributors should connect using the dedicated PostgreSQL `contributor`
role, not the main Supabase `postgres` administrator account.

### Connection details

Use the Supabase **Session Pooler** connection:

```text
Host: aws-0-eu-west-2.pooler.supabase.com
Port: 5432
Database: postgres
Username: contributor.oauiogqillkqiypkthyc
Password: provided privately by the project owner
```

Put these values in the **`REMOTE_DB_*`** variables, not in `DB_*`:

```env
REMOTE_DB_HOST=aws-0-eu-west-2.pooler.supabase.com
REMOTE_DB_PORT=5432
REMOTE_DB_NAME=postgres
REMOTE_DB_USER=contributor.oauiogqillkqiypkthyc
REMOTE_DB_PASSWORD=<password provided by the project owner>
```

Leave `DB_*` pointing at your local `smart_grocery` database if you run
ETL on this machine.

Or connect with `psql`:

```bash
psql "host=aws-0-eu-west-2.pooler.supabase.com port=5432 dbname=postgres user=contributor.oauiogqillkqiypkthyc"
```

The password is never stored in Git. Ask the project owner for it.

### Connect with pgAdmin

Register a new server only if you have not already registered this remote database.

The server **Name** is a local label in pgAdmin. It can be anything, for example `Smart Grocery Platform - Remote`.

On the connection tab, enter the Host, Port, Database, Username, and privately provided password from **Connection details** above.

### Shared tables

In pgAdmin, the shared tables are under:

```text
Databases → postgres → Schemas → grocery → Tables
```

The shared tables are:

- `products`
- `stores`
- `product_classification`
- `chain_prices`
- `price_comparison`

### Verify the connection

After connecting, run:

```sql
SELECT current_user;
```

This should return `contributor`.

Then confirm you can read the shared data:

```sql
SELECT COUNT(*)
FROM grocery.products;
```

### Security

- Never commit the database password to Git.
- Never put the password in source code, SQL files, or documentation.
- Application credentials should be stored in environment variables or a local `.env` file.
- The `.env` file must be ignored by Git.

---

## 5. Verify the setup

### Test the database connection

```bash
uv run python scripts/check_db_connection.py
```

Expected output includes a successful connection message and the connected database name.

### Run unit tests

```bash
uv run pytest
```

### Quick Python check

```bash
uv run python -c "import pandas, psycopg, requests; print('OK')"
```

---

## 6. Run the data extraction pipeline

Commands expect to be run from the **repository root** so paths like `data/raw/price_full/shufersal` resolve correctly.

The ETL is one CLI. It always runs extract → parse → load. Choose a chain
and an extract type (`prices_full`, `stores`, and `promo_full` are
implemented for all three chains).

### Run from Cursor (dropdowns)

1. Open the **Run and Debug** view (or press `F5`).
2. Select **ETL Pipeline**.
3. Choose the **chain**, then the **dataset**, then whether to download
   or reuse local files.

That uses the same `python -m src.etl` command as the terminal. Select
the project `.venv` interpreter if Cursor asks.

### Download, parse, and load PriceFull files

```bash
uv run python -m src.etl --chain shufersal --extract prices_full --max-pages 2 --max-files 3
uv run python -m src.etl --chain rami_levy --extract prices_full --max-files 3
uv run python -m src.etl --chain victory --extract prices_full --max-files 3
```

This will:

1. Extract PriceFull `.gz` files into `data/raw/price_full/<chain>/`
2. Parse products from the XML
3. Load staging, products, and product prices in PostgreSQL

Development defaults cap Shufersal pagination (`--max-pages 2`) and the
number of files (`--max-files 3`). Use `--full` for an unlimited run, or
`--no-download` to parse files already on disk.

See **[docs/etl_pipeline.md](etl_pipeline.md)** for flags and architecture.

### SuperCompare category crawl (optional)

This is **not** supermarket ETL. It downloads external category labels
used for product classification.

```bash
uv run python -m src.product_classification.supercompare
```

Output: `data/processed/supercompare_products.csv`. Resume is on by
default. Details: **[docs/supercompare_labeling.md](supercompare_labeling.md)**.

### Download, parse, and load PromoFull files

```bash
uv run python -m src.etl --chain shufersal --extract promo_full --max-pages 2 --max-files 3
uv run python -m src.etl --chain rami_levy --extract promo_full --max-files 3
uv run python -m src.etl --chain victory --extract promo_full --max-files 3
```

PromoFull files land in `data/raw/promo_full/<chain>/`. Rami Levy store
`039` is skipped. Rows land in `grocery.promotions`,
`grocery.promotion_groups`, and `grocery.promotion_items` (see
**[docs/etl_pipeline.md](etl_pipeline.md#grocerypromotions)**).

### List downloaded price files

```bash
uv run python scripts/inspect_price_files.py
```

### Reload from staging with SQL (optional)

The Python loader already writes staging → products → product prices.
The SQL scripts remain available for manual re-runs:

```bash
psql -h localhost -U postgres -d smart_grocery -f sql/03_load_products.sql
psql -h localhost -U postgres -d smart_grocery -f sql/04_load_product_prices.sql
psql -h localhost -U postgres -d smart_grocery -f sql/07_data_quality_checks.sql
```

---

## Daily workflow cheat sheet

```bash
cd smart-grocery-platform
uv sync                          # refresh deps after pull (if lock changed)
# edit .env if DB settings change
uv run python scripts/check_db_connection.py
uv run python -m src.etl --chain shufersal --extract prices_full --max-pages 2 --max-files 3
```

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| Wrong Python version | Run `uv python install 3.11` then `uv sync` again |
| `ModuleNotFoundError` | Run commands with `uv run` from the repo root, or `source .venv/bin/activate` |
| Connection failed | Confirm PostgreSQL is running, `.env` values match, and the database exists |
| Missing `data/raw/` paths | Create dirs or run extraction from the repo root (scripts create folders as needed) |
| Import errors in extraction scripts | Run from repo root with `uv run python -m src.etl ...` |

---

## Project dependency summary

Declared in `pyproject.toml` (`requires-python = ">=3.11"`):

- `beautifulsoup4`, `lxml` — HTML/XML parsing
- `pandas` — CSV export and analysis
- `psycopg[binary]` — PostgreSQL driver
- `python-dotenv` — load `.env`
- `requests` — HTTP downloads
