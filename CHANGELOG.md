# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added a conservative Tableau extract of 5,676 audit-valid three-chain
  products (`data/processed/tableau_verified_three_chains.csv`); the
  original extract, classifications, and workbook are unchanged
- Added an illustrative 13-line weekly basket comparison
  (`data/processed/weekly_basket_comparison.csv`,
  `docs/weekly_basket_results.md`); potatoes and chicken excluded;
  audit and workbook unchanged
- Added streaming grocery analytical chat service and web UI

- Added an interactive Web Chat UI served directly by FastAPI at `/` and `/ui`,
  supporting live SSE token streaming, collapsible tool execution and query
  result badges, conversational multi-turn history, Markdown rendering, and
  Hebrew/English text support with zero external frontend dependencies
- Added a streaming chat service (`uv run python -m src.agent_platform`) that
  answers grocery price questions in plain language from the shared analytical
  database, served with FastAPI over Server-Sent Events
- Added a pydantic-ai agent combining a `SkillsToolset` of three `SKILL.md`
  playbooks (`grocery-database`, `price-comparison`, `chain-competitiveness`)
  with a `FunctionToolset` of five read-only SQL tools; there is no free-form
  SQL tool and `run_skill_script` is excluded
- Added read-only database access for the agent: `default_transaction_read_only`
  and `statement_timeout` are set as server-side session options on a pooled
  async connection, so no tool can write or run an unbounded query
- Added explicit context control through a `ProcessHistory` capability that
  trims history by whole conversation turns, preserving `ToolCallPart` and
  `ToolReturnPart` pairing, and audits every outbound model request
- Added `GET /conversations/{id}/context` so the exact payload a next turn
  would send to the model can be inspected
- Added per-conversation token-bucket rate limiting with an injected clock,
  alongside per-run `UsageLimits` for requests, tool calls and tokens
- Added a `ChatServiceError` hierarchy where each error owns its `ErrorCode`
  and HTTP status, with one wire payload shared by HTTP responses and SSE
  `error` events
- Added `docs/agent_platform.md` and ADR 0007 for the chat service
- Added a first 12-class main-category experiment (`item_name` vs
  `item_name` + `manufacture_name`, TF-IDF + Logistic Regression / Linear
  SVM / Naive Bayes) in `product_classifier_experiments.md`, recorded as
  ADR 0006
- Added a Test-set error analysis of the winning Linear SVM
  (`docs/product_classifier_error_analysis.md`)
- Added a manual main-category overlay for 13 approved SuperCompare
  errors (`src/product_classification/manual_category_corrections.csv`);
  cigarettes stay on the existing analysis denylist
- Added a documentation map (`docs/README.md`) and expanded guides for
  the current SuperCompare labeling phase, local vs remote `.env`
  variables, and ADR reading order
- Added Stores and PromoFull ETL for Shufersal, Rami Levy, and Victory
- Added a unified ETL `Pipeline` with Strategy + Factory composition (`python -m src.etl`)
- Added ADR 0001 for pipeline orchestration
- Added `CONTRIBUTING.md` with object-oriented and modeling conventions
- Added review skills, ETL unit tests, and a database connection check
- Added Shufersal Stores extract, parse, and `grocery.stores` load
- Added Rami Levy Stores extract via Cerberus FTP
- Added Victory Stores extract via the laibcatalog HTTP API
- Added a Cursor/VS Code **ETL Pipeline** launcher with chain and extract dropdowns
- Added PromoFull extract, parse, and load for Shufersal, Rami Levy, and Victory

### Changed

- Added `fastapi`, `sse-starlette` and `uvicorn` dependencies, and enabled the
  `pool` extra on `psycopg` for async connection pooling
- Replaced per-chain ETL scripts with a unified `python -m src.etl` Pipeline

- Replaced per-chain `process_*.py` scripts with chain extractors and shared parse/load strategies
- PriceFull load (staging, validation, upserts) now runs inside `PriceFullLoader`

### Fixed

### Removed

- Removed `process_shufersal.py`, `process_rami_levy.py`, `process_victory.py`, and `scripts/run_shufersal_dev.py`
- Removed CSV export from the default ETL run

### Security

- The chat service agent cannot write to the database or compose SQL: every
  statement is a named `%s`-parameterized constant, the connection is read-only
  and statement-timed server-side, skill script execution is disabled, and
  driver errors are wrapped so connection details are never returned to a
  client
