# Contributing

This project treats ETL as software: small objects with clear
responsibilities, tests around behavior, and named constants instead of
magic values.

## Design principles

### Encapsulate features as objects

Main capabilities live on objects, not in script-shaped `main()` files.

- `Pipeline` always runs extract → parse → load.
- Chain downloaders implement `Extractor`.
- Dataset parsers implement `Parser`.
- Dataset loaders implement `Loader`.
- `PipelineFactory` composes those strategies from `Chain` and
  `ExtractType`.

A new chain should add an extractor. A new extract type should add a
parser and a loader (and extractor behavior for that file type). Do not
copy the three pipeline steps into another script.

Durable architecture choices belong in an ADR under `docs/adr/`. See
[0001. ETL pipeline orchestration](docs/adr/0001-etl-pipeline-orchestration.md).

### No hardcoded strings or values in logic

URLs, timeouts, file globs, CLI defaults, table-facing labels, and user
messages are named constants in config modules such as
`src/data_extraction/data_extraction_config.py` and `src/etl/constants.py`.

Closed sets of choices are enums (`Chain`, `ExtractType`,
`ShufersalPriceCategory`), not raw strings compared around the codebase.

### Every component needs unit tests

New classes and public functions need tests in `test/unit/`.

- Test expected behavior and important failure paths.
- Replace HTTP, FTP, and PostgreSQL with fakes or mocks.
- Tests must be deterministic.
- Do not require a live database for unit tests.

Run them from the repository root:

```bash
uv run pytest
```

## Data modeling: objects, dicts, dataclasses, Pydantic, enums

### Objects vs dicts

Use objects for public APIs and domain records. Dicts are only for
ephemeral local grouping, or for payloads that arrive as JSON from an
external API at the system boundary (for example Victory file listings)
before they are converted into objects.

Do not pass anonymous dicts through parsers, loaders, or the pipeline.

### Dataclass vs Pydantic

Use **dataclasses** for internal records the application already trusts:

- `PriceFullProduct`, `FileMetadata`, `Store`, `Promotion`,
  `PromotionGroup`, `PromotionItem`
- `PipelineOptions`, `DailySnapshot`

Use **Pydantic** only at untrusted or external boundaries (incoming HTTP
bodies, config files, third-party payloads that need validation). Do not
add Pydantic for objects that never leave the process.

### Enum vs dataclass

Use an **enum** when the set of values is closed and known at compile
time (`Chain`, `ExtractType`).

Use a **dataclass** when the record has several fields and is not a
fixed vocabulary.

## Running the pipeline

From Cursor, use **Run and Debug → ETL Pipeline** and pick the chain and
dataset from the dropdowns.

From the repository root:

```bash
uv run python -m src.etl --chain shufersal --extract prices_full --max-pages 2 --max-files 3
```

`--extract stores` and `--extract promo_full` are implemented for Shufersal,
Rami Levy, and Victory (extract, parse, and load). Rami Levy store 039 is
skipped for PromoFull.
