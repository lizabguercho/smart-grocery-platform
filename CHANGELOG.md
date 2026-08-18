# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

- Replaced per-chain ETL scripts with a unified `python -m src.etl` Pipeline

- Replaced per-chain `process_*.py` scripts with chain extractors and shared parse/load strategies
- PriceFull load (staging, validation, upserts) now runs inside `PriceFullLoader`

### Fixed

### Removed

- Removed `process_shufersal.py`, `process_rami_levy.py`, `process_victory.py`, and `scripts/run_shufersal_dev.py`
- Removed CSV export from the default ETL run

### Security
