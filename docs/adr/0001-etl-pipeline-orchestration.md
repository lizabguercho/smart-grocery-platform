# 0001. ETL pipeline orchestration

## Status

Accepted

## Context

Each supermarket chain had its own process script (`process_shufersal.py`,
`process_rami_levy.py`, `process_victory.py`). Download logic differed by
chain, but parse, optional CSV export, staging load, validation, product
load, price load, and staging cleanup were copied in each file.

That shape had three problems:

1. The pipeline was not one algorithm. Step order lived in three `main()`
   functions, so a missed step or a drifted sequence was easy.
2. Extract type was not a first-class choice. Every run assumed PriceFull
   files. Stores (and later promos) could not be selected without another
   copy of the workflow.
3. Tests had to patch a script-shaped `main()` instead of a small
   orchestrator with replaceable collaborators.

We needed one place that always runs extract → parse → load, while still
letting callers choose a chain and an extract type.

## Decision

Use three complementary patterns:

1. **Pipeline (template method).** A `Pipeline` object always runs
   extract, then parse, then load. It owns step order, progress
   reporting, and fail-fast behavior. Loader-internal work such as
   staging, validation, and upserts stays inside the PriceFull loader.
2. **Strategy.** `Extractor`, `Parser`, and `Loader` are interchangeable
   implementations. Chains differ in *how* files are obtained. Extract
   types differ in *what* is parsed and loaded.
3. **Factory.** `PipelineFactory` composes the matching trio from
   `Chain`, `ExtractType`, and `PipelineOptions`.

A Pipeline object is the composition root for a run. Callers (CLI or
tests) do not wire steps themselves. New chains add an extractor. New
extract types add a parser and a loader, plus extractor behavior for
that file type.

Stores is a reserved extract type: selectable through the same factory
and interfaces, but implementations raise `NotImplementedError` until a
follow-up delivers download, parse, and load.

CSV export is not a pipeline step.

## Why a Pipeline object

- One class guarantees the three steps occur in order.
- Fail-fast is trivial to test: if extract raises, parse and load are
  not called.
- The object can be constructed with fakes, so orchestration tests do
  not touch HTTP, FTP, or PostgreSQL.
- Progress and error handling have a single home instead of three
  scripts.

## Rejected alternatives

- **Inheritance per chain** (`ShufersalPipeline`, `VictoryPipeline`).
  Adding Stores would require a subclass per chain and extract type.
- **Factory only.** A factory can create objects, but it does not
  guarantee that extract → parse → load lives in one algorithm.
- **Strategy only.** Strategies need a composition point for
  “Shufersal + PriceFull” versus “Victory + Stores”.
- **Keep `process_*.py` files.** That preserves the duplication this
  decision exists to remove.

## Consequences

- The CLI is `python -m src.etl` with `--chain` and `--extract`.
- Durable ETL orchestration rules belong in `src/etl/`. Chain download
  details stay in `src/data_extraction/<chain>/`.
- Stores can be chosen today, but a run fails with a clear
  `NotImplementedError` until that strategy is implemented.
- Adding a chain should not copy parse or load logic.
- Adding an extract type should not copy chain download transport.
