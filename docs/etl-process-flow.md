# ETL process flow

This is a working map of one pipeline run: **extract → parse → load**.

Use it while building Stores. Fill in the Parse and Load sections as those
steps are implemented.

Architecture details live in [etl_pipeline.md](etl_pipeline.md) and
[ADR 0001](adr/0001-etl-pipeline-orchestration.md).


## The three steps

Every run is the same, no matter which supermarket or dataset:

```text
extract  →  parse  →  load
get files → read XML → save to PostgreSQL
```

You choose:

- **chain:** `shufersal`, `rami_levy`, or `victory`
- **extract type:** `prices_full`, `stores`, or `promo_full`

Example:

```bash
uv run python -m src.etl --chain shufersal --extract stores --max-pages 2 --max-files 3
```

In Cursor, **Run and Debug → ETL Pipeline** asks for the same choices
with dropdowns.

Raw files land by extract type, then by chain:

| Extract type | Shufersal | Rami Levy | Victory |
|---|---|---|---|
| `prices_full` | `data/raw/price_full/shufersal/` | `data/raw/price_full/rami_levy/` | `data/raw/price_full/victory/` |
| `stores` | `data/raw/stores/shufersal/` | `data/raw/stores/rami_levy/` | `data/raw/stores/victory/` |
| `promo_full` | `data/raw/promo_full/shufersal/` | `data/raw/promo_full/rami_levy/` | `data/raw/promo_full/victory/` |


## Who does what

```text
you type a command
        ↓
src/etl/cli.py                 reads --chain and --extract
        ↓
src/etl/factory.py             picks extractor + parser + loader
        ↓
src/etl/pipeline.py            always: extract(), then parse(), then load()
        ↓
   ┌────────────┬────────────┬────────────┐
   │  Extract   │   Parse    │    Load    │
   └────────────┴────────────┴────────────┘
```

| Role | Question it answers | Picked by |
|---|---|---|
| Extractor | How do I get the files? | chain |
| Parser | How do I read those files? | extract type |
| Loader | How do I save the records? | extract type |

The pipeline does not download or parse. It only calls the three objects
in order. If extract fails, parse and load are not called.


## Step 1. Extract  ✅ Shufersal, Rami Levy, and Victory Stores

### Shared routing

`src/data_extraction/chain_extractor.py` is the front door for every chain:

```text
if extract type is stores      →  extract_stores()
if extract type is promo_full  →  extract_promo_full()
otherwise                      →  extract_price_full()
```

`extract_promo_full()` is abstract. Every chain implements it.
The base `extract_stores()` raises `NotImplementedError`. A chain turns
Stores on by overriding that method.

| Chain | PriceFull extract | Stores extract | PromoFull extract |
|---|---|---|---|
| Shufersal | implemented | implemented | implemented |
| Rami Levy | implemented | implemented | implemented (skips store 039) |
| Victory | implemented | implemented | implemented |

### Shufersal Stores path

Command: `--chain shufersal --extract stores`

```text
cli.py
  → factory.py builds ShufersalExtractor
  → pipeline.py calls extractor.extract()
  → chain_extractor.py calls extract_stores()
  → shufersal/extractor.py extract_stores()
       │
       ├── download=True (default)
       │     get_all_stores_links()      listing pages, category STORES=5
       │     download_store_files()      newest snapshot → data/raw/stores/shufersal/
       │
       └── --no-download
             list_local_stores_files()   *Stores* already in data/raw/stores/shufersal/
```

Files:

| File | Job |
|---|---|
| `src/etl/cli.py` | Read flags |
| `src/etl/factory.py` | Create `ShufersalExtractor` |
| `src/etl/pipeline.py` | Call `extract()` |
| `src/data_extraction/chain_extractor.py` | Route Stores vs PriceFull |
| `src/data_extraction/shufersal/extractor.py` | Shufersal shopper (`extract_stores`) |
| `src/data_extraction/shufersal/download.py` | Website listing + HTTP download |
| `src/data_extraction/snapshots.py` | Read date/time from the filename |
| `src/data_extraction/local_files.py` | Find files already on disk |
| `src/data_extraction/data_extraction_config.py` | URLs, folders, prefixes |

Shufersal Stores filenames are shorter than PriceFull:

```text
PriceFull:  PriceFull7290027600007-001-001-20260722-030000.gz
Stores:     Stores7290027600007-000-20260816-020.gz
```

The Stores parser accepts 4 parts. Shufersal publishes one Stores file
for the whole chain, not one file per store.

Verified download:

```text
data/raw/stores/shufersal/Stores7290027600007-000-20260816-020.gz
```

### Rami Levy Stores path

Command: `--chain rami_levy --extract stores`

```text
cli.py
  → factory.py builds RamiLevyExtractor
  → pipeline.py calls extractor.extract()
  → chain_extractor.py calls extract_stores()
  → rami_levy/extractor.py extract_stores()
       │
       ├── download=True (default)
       │     download_store_files()      FTP listing → data/raw/stores/rami_levy/
       │
       └── --no-download
             list_local_stores_files()   *Stores* already in data/raw/stores/rami_levy/
```

Files:

| File | Job |
|---|---|
| `src/data_extraction/rami_levy/extractor.py` | Rami Levy shopper (`extract_stores`) |
| `src/data_extraction/rami_levy/download.py` | Cerberus FTP listing + download |

Parse and load are the same as Shufersal. Only the download transport is
different (FTP instead of HTTP). Rami Levy Stores files are uncompressed
`.xml`, not `.gz`.

### Victory Stores path

Command: `--chain victory --extract stores`

```text
cli.py
  → factory.py builds VictoryExtractor
  → pipeline.py calls extractor.extract()
  → chain_extractor.py calls extract_stores()
  → victory/extractor.py extract_stores()
       │
       ├── download=True (default)
       │     list_store_files()          API fileType=stores
       │     download_store_files()      newest snapshot → data/raw/stores/victory/
       │
       └── --no-download
             list_local_stores_files()   *Stores* already in data/raw/stores/victory/
```

Files:

| File | Job |
|---|---|
| `src/data_extraction/victory/extractor.py` | Victory shopper (`extract_stores`) |
| `src/data_extraction/victory/download.py` | laibcatalog API listing + HTTP download |

Parse and load are the same as the other chains. Victory publishes one
gzipped Stores file for the whole chain. The date and time in the
filename can be glued together (`20260816060100`); snapshot selection
uses the API `fileDate` instead, and parse takes the first eight digits
as `YYYYMMDD`.

Verified download:

```text
data/raw/stores/victory/Stores7290696200003-000-20260816060100-060100.gz
```


## Step 2. Parse  ✅ shared Stores XML reader

After extract, `pipeline.py` calls `parser.parse(files)`.

The factory already picks `StoresParser`. That class now calls
`parse_store_files()`.

```text
pipeline.py parser.parse(files)
  → parsers/stores.py StoresParser
  → store_parser.py parse_store_files()
       open each .gz
       read Chain / SubChain / Store XML
       build Store records
```

| File | Job |
|---|---|
| `src/data_extraction/models.py` | `Store` dataclass (one row per shop) |
| `src/data_extraction/store_parser.py` | Read gzipped XML into `Store` objects |
| `src/data_extraction/parsers/stores.py` | Pipeline wrapper (`StoresParser`) |

XML shape (simplified):

```text
Chain
  ChainID, ChainName
  SubChains
    SubChain
      SubChainID, SubChainName
      Stores
        Store
          StoreID, StoreName, Address, City, ZIPCode, ...
```

Each `<Store>` becomes one `Store` record. Chain and sub-chain fields
are copied onto every store. `source_file` and `extraction_date` come
from the filename.

How to try parse with files already downloaded:

```bash
uv run python -m src.etl --chain shufersal --extract stores --no-download
```

Create `grocery.stores` first (step 3), or load will fail after parse
prints the record count.


## Step 3. Load  ✅ `grocery.stores`

After parse, `pipeline.py` calls `loader.load(records)`.

There is no staging table for stores. The loader upserts directly.

```text
pipeline.py loader.load(records)
  → stores_loader.py StoresLoader
  → loader.py load_stores()
       skip rows missing chain_id or store_id
       INSERT INTO grocery.stores
       ON CONFLICT (chain_id, store_id) UPDATE
```

| File | Job |
|---|---|
| `sql/02_create_tables.sql` | `grocery.stores` table |
| `src/database_loader/stores_loader.py` | Pipeline wrapper (`StoresLoader`) |
| `src/database_loader/loader.py` | `load_stores()` SQL upsert |

Primary key: `(chain_id, store_id)`. A later run updates name, address,
and the other fields. This is latest-known store metadata, not history.

Create the table once:

```bash
psql -h localhost -U postgres -d smart_grocery -f sql/02_create_tables.sql
```

Then run the pipeline:

```bash
uv run python -m src.etl --chain shufersal --extract stores --no-download
```


## PromoFull  ✅ Shufersal, Rami Levy, and Victory

PromoFull uses the same extract → parse → load path as Stores.

```bash
uv run python -m src.etl --chain shufersal --extract promo_full --full
uv run python -m src.etl --chain rami_levy --extract promo_full --full
uv run python -m src.etl --chain victory --extract promo_full --full
```

Shared parse reads gzipped PromoFull XML into `Promotion` records with
nested `PromotionGroup` and `PromotionItem` objects. Load upserts:

- `grocery.promotions`
- `grocery.promotion_groups`
- `grocery.promotion_items`

Rami Levy store `039` is skipped. Incremental `Promo` files are not
implemented.

| File | Job |
|---|---|
| `src/data_extraction/promotion_parser.py` | Read gzipped XML into promotion objects |
| `src/data_extraction/parsers/promo_full.py` | Pipeline wrapper (`PromoFullParser`) |
| `src/database_loader/promotions_loader.py` | Pipeline wrapper (`PromoFullLoader`) |
| `src/database_loader/loader.py` | `load_promotions()` SQL upserts |
| `sql/02_create_tables.sql` | Promotion tables |

