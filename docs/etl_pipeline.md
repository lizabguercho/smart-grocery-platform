# ETL Pipeline

## Overview

The Smart Grocery Platform ETL downloads official supermarket files,
parses them into domain records, and loads them into PostgreSQL.

Every run is the same three steps:

```text
extract → parse → load
```

Callers choose a **chain** (`shufersal`, `rami_levy`, `victory`) and an
**extract type** (`prices_full` or `stores`). PriceFull is fully
implemented. Stores is a reserved strategy that raises
`NotImplementedError` until a follow-up implements download, parse, and
load.

High-level PriceFull flow:

```text
Chain sources
→ chain-specific extract
→ shared XML parse (PriceFullProduct)
→ grocery.products_staging
→ grocery.products
→ grocery.product_prices
```

![ETL Pipeline Architecture](images/etl_pipeline.png)

> Note: the image above is still Shufersal-era. Prefer the architecture
> diagram in this document until the PNG is regenerated.

The orchestration decision is recorded in
[ADR 0001](adr/0001-etl-pipeline-orchestration.md).


## Architecture Principles

- **Pipeline:** `Pipeline` always runs extract → parse → load.
- **Strategy:** `Extractor`, `Parser`, and `Loader` are interchangeable.
- **Factory:** `PipelineFactory` wires the trio from `Chain` +
  `ExtractType` + `PipelineOptions`.
- **Chain-specific:** how files are downloaded or discovered.
- **Extract-type-specific:** how files are parsed and loaded.
- **CLI:** `uv run python -m src.etl --chain <chain> --extract <type>`


## How to run

From the repository root:

```bash
uv run python -m src.etl --chain shufersal --extract prices_full --max-pages 2 --max-files 3
uv run python -m src.etl --chain rami_levy --extract prices_full --max-files 3
uv run python -m src.etl --chain victory --extract prices_full --no-download
uv run python -m src.etl --chain shufersal --extract stores
```

| Flag | Meaning |
|------|---------|
| `--chain` | `shufersal`, `rami_levy`, or `victory` |
| `--extract` | `prices_full` (default) or `stores` |
| `--max-files` | Download cap after latest-per-store selection (default `3`) |
| `--max-pages` | Shufersal listing-page cap (default `2`; ignored by other chains) |
| `--full` | No `max-files` or `max-pages` limit |
| `--download` / `--no-download` | Download sources, or use files already in `data/raw/<chain>/` |


## Chain Extraction Methods

| Chain | Access method | Source | Raw directory |
|-------|---------------|--------|---------------|
| Shufersal | HTTP (HTML category pages → file links) | `prices.shufersal.co.il` | `data/raw/shufersal` |
| Rami Levy | FTP (Cerberus published prices) | `url.retail.publishedprices.co.il` | `data/raw/rami_levy` |
| Victory | HTTP JSON API + file download | `laibcatalog.co.il` | `data/raw/victory` |

Each chain stores downloaded PriceFull `.gz` files in its own raw
directory. Existing local files can be skipped on re-download. Downloaders
keep one latest snapshot per store for the latest available date.


## Shared Transform

All supported chains publish PriceFull XML with the same item schema.

- **Model:** `PriceFullProduct` and `FileMetadata` in
  `src/data_extraction/models.py`
- **Parser:** `PriceFullParser` wrapping `parse_price_full_files()` in
  `src/data_extraction/price_full_parser.py`

The parser opens each gzipped XML file, reads store/chain metadata from
the file root, and builds one `PriceFullProduct` per `<Item>`.


## Architecture Diagram

```mermaid
flowchart TD
    CLI["python -m src.etl --chain --extract"] --> Factory[PipelineFactory]
    Factory --> Pipeline[Pipeline.run]
    Pipeline --> Extract[Extractor.extract]
    Extract --> Parse[Parser.parse]
    Parse --> Load[Loader.load]

    Extract --> S[Shufersal HTTP]
    Extract --> R[Rami Levy FTP]
    Extract --> V[Victory API]

    S --> RS[data/raw/shufersal]
    R --> RR[data/raw/rami_levy]
    V --> RV[data/raw/victory]

    RS --> Parse
    RR --> Parse
    RV --> Parse

    Parse --> ST[grocery.products_staging]
    ST --> PR[grocery.products]
    ST --> PP[grocery.product_prices]
```


## Pipeline Steps

The `Pipeline` object always performs these three steps.

### 1. Extract

A chain `Extractor` downloads or locates files for the selected extract
type and returns local paths under `data/raw/<chain>/`.

### 2. Parse

A shared `Parser` for that extract type turns files into domain records
(`PriceFullProduct` today; `Store` when Stores is implemented).

### 3. Load

A shared `Loader` for that extract type writes records to PostgreSQL.
CSV export is not part of the pipeline.

### PriceFull loader internals

`PriceFullLoader` still uses staging and validation. Those are loader
details, not extra pipeline steps:

1. Truncate and load `grocery.products_staging`
2. `validate_staging()`
3. Upsert `grocery.products`
4. Upsert `grocery.product_prices`
5. `validate_product_prices()`
6. Clear staging

**Staging decision:**  
The staging table represents only the current extraction and is not
used for historical storage.

`validate_staging()` rejects rows with NULL `item_code`, `store_id`,
`extraction_date`, or `item_price`.

Unique products are loaded from staging into `grocery.products`.
`item_code` is the primary key.

If a product does not exist, it is inserted. If it already exists, its
metadata is updated using the latest extraction.

**Products decision:**  
The `products` table represents the latest known product metadata.
Fields such as product name, manufacturer, quantity, and unit of measure
may change over time, so existing products are updated rather than ignored.

Historical prices are not stored here. Price history is preserved in
`grocery.product_prices`.

Price observations are loaded into `grocery.product_prices`.
A price record is uniquely identified by:

`chain_id + store_id + item_code + extraction_date`

**Same-day snapshot deduplication:**  
When staging contains multiple snapshots for the same key on the same
day, the loader uses:

```sql
SELECT DISTINCT ON (chain_id, store_id, item_code, extraction_date)
...
ORDER BY chain_id, store_id, item_code, extraction_date, source_file DESC
```

so one row per key is kept (latest `source_file` wins).

If the same key is loaded again later, `ON CONFLICT` updates the existing
row instead of inserting a duplicate.

**Prices decision:**  
Unlike the staging table, `product_prices` keeps historical observations
so prices can be analyzed over time.

`validate_product_prices()` checks that every price row references an
existing product (`item_code` foreign key relationship).


## Data Flow

```text
grocery.products_staging
        |
        +----> grocery.products
        |
        +----> grocery.product_prices
```


## Database Tables

### `grocery.products_staging`

Temporary landing table for the current extraction run. Truncated before
each load.

### `grocery.products`

One row per unique product (`item_code`). Holds the latest known product
metadata.

### `grocery.product_prices`

Historical price observations.

Primary key:

`(chain_id, store_id, item_code, extraction_date)`


## Validation

| Check | Purpose |
|-------|---------|
| `validate_staging()` | Fail early on NULL required staging fields |
| `validate_product_prices()` | Fail if any price has no matching product |


## Data Quality Rules

- `item_code` cannot be NULL in final tables.
- `store_id` cannot be NULL for price records.
- `chain_id` cannot be NULL for price records.
- `extraction_date` cannot be NULL for price records.
- Every price record must reference an existing product.
- Duplicate `(chain_id, store_id, item_code, extraction_date)` records are
  prevented by the database primary key.
- Same-day duplicate snapshots are reduced to one row during load
  (`DISTINCT ON` + `source_file DESC`).


## Future Improvements

- Implement the Stores extract type (download, parse, `grocery.stores`,
  load).
- Regenerate `images/etl_pipeline.png` for the multi-chain Pipeline
  architecture.
- Create cross-chain product matching and normalization.
- Add English/Russian product names for dashboard use.
- Improve bulk-loading performance if necessary.
