# 0003. Remote analytical database

## Status

Accepted

This record will be updated if the hosted provider, shared table set,
or contributor access model changes.

Related: [remote_database_architecture.md](../remote_database_architecture.md) ·
[Documentation map](../README.md)

## Context

The local PostgreSQL database is the ETL environment. After loading
Shufersal, Rami Levy, and Victory it is about **4.1 GB**, mostly
historical store-level prices and promotion details.

Two people work on the project. They need the same product list, chain
prices, and (later) product categories. They do not need the full
history on every machine.

Copying 4.1 GB, keeping two local databases in sync by hand, or putting
raw dumps in Git is not workable. A hosted PostgreSQL instance can hold
a small analytical subset if the table list is deliberate.

The analysis and classification work needs:

- `grocery.products` — product names and attributes for the shared
  catalog
- `grocery.stores` — chain/store reference
- `grocery.chain_prices` — median price per item × chain
- `grocery.price_comparison` (~14.8k rows) — one row per product that
  appears in **at least two chains**. This is the set used for
  cheapest-chain analysis and for **product categorization**.
- `grocery.product_classification` — shared category labels for those
  comparable products

Those tables are about **25 MB**.

## Decision

Use **two PostgreSQL layers**:

1. **Local database** — source of truth for raw files after ETL:
   history, staging, promotions, rebuilds, validation.
2. **Remote database (Supabase, PostgreSQL)** — shared analytical
   layer only. Rebuild locally, then sync the small tables.

Supabase was chosen because it is hosted PostgreSQL (same SQL as local),
the ~25 MB subset fits a free tier, and contributors can connect with
ordinary Postgres tools (`psycopg`, psql, pgAdmin).

A dedicated **`contributor` role** has read/write on the shared
`grocery` schema. Credentials live in `.env`
(`REMOTE_DB_*`), never in Git. Python uses
`get_remote_connection()`.

The remote database is **not** the source of truth for supermarket
files. Refresh path:

```text
download files → local ETL → rebuild chain_prices
→ rebuild price_comparison → sync selected tables remotely
```

Classification is read and written remotely so both contributors share
the same `product_classification` rows.

## Why this split

```text
LOCAL (~4.1 GB)          REMOTE (~25 MB)
raw + history            products
staging                  stores
product_prices           chain_prices
promotions               price_comparison
                         product_classification
```

- Contributors do not download gigabytes to classify products or run
  comparison SQL.
- The shared instance stays small enough for free hosted Postgres.
- Historical prices remain available locally if a later analysis needs
  them.
- Analytical tables can be rebuilt when new extracts land.

Tables left local on purpose (too large or ETL-only):
`product_prices` (~2.4 GB), promotion tables (~1.7 GB combined),
staging.

## Rejected alternatives

- **Sync the full 4.1 GB remotely.** Exceeds a cheap hosted database,
  slow to clone, and most rows are unused for current analysis.
- **Each contributor keeps only a local database.** Labels and analysis
  tables would diverge immediately.
- **Commit CSV/Parquet dumps to Git.** Large, awkward for SQL joins,
  and a poor place for credentials-free collaboration on live tables.
- **SQLite file in the repo.** Easier to copy, but not the project’s
  PostgreSQL model, and still a merge conflict on every classification
  write.
- **Google Sheets / Airtable as the shared layer.** Fine for a few
  hundred rows, not for ~14k comparable products plus prices.
- **A shared cloud VM running full local Postgres.** Operationally
  heavier than Supabase for a two-person project, and would still
  waste space on history nobody queries remotely.
- **Remote as the ETL target.** The pipeline writes staging and
  history. That belongs on the machine that downloads the files.

## Consequences

- New ETL data is invisible remotely until the analytical tables are
  rebuilt and synced.
- Classification work should use `get_remote_connection()` so both
  contributors see the same labels.
- If a query needs store-level history or promotions, run it locally.
- If the shared table list grows (for example a dashboard extract),
  revisit size against the hosted quota.
- Security: `.env` stays gitignored; the contributor role should not
  need superuser access.
