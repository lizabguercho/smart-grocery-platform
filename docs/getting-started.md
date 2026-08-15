# Getting Started

This guide covers setting up a local development environment for Smart Grocery Platform using **uv**, **Python 3.11**, and **PostgreSQL**.

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

Database credentials are loaded from a `.env` file in the project root (see `src/database/connection.py`).

Copy the example file and edit values to match your local PostgreSQL setup:

```bash
cp .env.example .env
```

Example contents:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=smart_grocery
DB_USER=postgres
DB_PASSWORD=your_password_here
```

`.env` is gitignored — never commit real credentials.

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
| `02_create_tables.sql` | Creates `products`, `product_prices`, and staging tables |
| `03_load_products.sql` | Loads products from staging (after you load staging data) |
| `04_load_product_prices.sql` | Loads prices from staging |
| `05_indexes.sql` | Creates indexes on `product_prices` |
| `07_data_quality_checks.sql` | Validation queries |
| `inspection_queries.sql` | Ad-hoc inspection queries |

---

## 5. Verify the setup

### Test the database connection

```bash
uv run python -m src.database.test_connection
```

Expected output includes a successful connection message and the connected database name.

### Quick Python check

```bash
uv run python -c "import pandas, psycopg, requests; print('OK')"
```

---

## 6. Run the data extraction pipeline

Scripts expect to be run from the **repository root** so paths like `data/raw/shufersal` resolve correctly.

### Download and parse Shufersal PriceFull files

```bash
uv run python src/data_extraction/process_shufersal.py
```

This will:

1. Fetch the Shufersal prices page
2. Download PriceFull `.gz` files into `data/raw/shufersal/`
3. Parse products from the XML
4. Write a CSV to `data/processed/shufersal_products.csv`

### List downloaded price files

```bash
uv run python scripts/inspect_price_files.py
```

### Load into PostgreSQL (after staging is populated)

Once raw data has been loaded into `grocery.products_staging`:

```bash
psql -h localhost -U postgres -d smart_grocery -f sql/03_load_products.sql
psql -h localhost -U postgres -d smart_grocery -f sql/04_load_product_prices.sql
psql -h localhost -U postgres -d smart_grocery -f sql/07_data_quality_checks.sql
```

> Note: Automating the CSV → staging load is part of the planned pipeline work. Today, create/load staging via SQL/`COPY` as needed for your workflow.

---

## Daily workflow cheat sheet

```bash
cd smart-grocery-platform
uv sync                          # refresh deps after pull (if lock changed)
# edit .env if DB settings change
uv run python -m src.database.test_connection
uv run python src/data_extraction/process_shufersal.py
```

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| Wrong Python version | Run `uv python install 3.11` then `uv sync` again |
| `ModuleNotFoundError` | Run commands with `uv run` from the repo root, or `source .venv/bin/activate` |
| Connection failed | Confirm PostgreSQL is running, `.env` values match, and the database exists |
| Missing `data/raw/` paths | Create dirs or run extraction from the repo root (scripts create folders as needed) |
| Import errors in extraction scripts | Run from repo root; those modules currently use local imports within `src/data_extraction/` |

---

## Project dependency summary

Declared in `pyproject.toml` (`requires-python = ">=3.11"`):

- `beautifulsoup4`, `lxml` — HTML/XML parsing
- `pandas` — CSV export and analysis
- `psycopg[binary]` — PostgreSQL driver
- `python-dotenv` — load `.env`
- `requests` — HTTP downloads
