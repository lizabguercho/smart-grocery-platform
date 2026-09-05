# 0002. Three chains and data extraction

## Status

Accepted

This record will be updated if another chain is added or if the
extract sources change.

Related: [etl_pipeline.md](../etl_pipeline.md) ·
[Documentation map](../README.md)

## Context

The project compares grocery prices so a shopper can see where the same
product is cheaper. That requires more than one supermarket. It also
requires a legal, repeatable way to collect prices.

Israeli food retailers publish official price, store, and promotion
files under price-transparency rules. The common artifacts are gzipped
XML dumps:

- PriceFull — store-level product prices
- Stores — store and chain reference data
- PromoFull — promotions

Many chains publish these files. Ingesting all of them would turn the
project into a retailer-coverage exercise. The goal is a Data Analyst
portfolio: a complete pipeline and a cross-chain price analysis, not
every Israeli supermarket.

The three chains also expose files in different ways. Extraction has to
respect that without copying parse and load logic for each retailer
(see [ADR 0001](0001-etl-pipeline-orchestration.md)).

## Decision

### Which chains

Collect data from exactly three chains:

1. **Shufersal** — large national supermarket; prices published over
   HTTP as HTML listing pages with file links
   (`prices.shufersal.co.il`).
2. **Rami Levy** — discount-oriented chain; a useful contrast to
   Shufersal on price. Files come from Cerberus FTP
   (`url.retail.publishedprices.co.il`).
3. **Victory** — another national chain, reached through a JSON file
   catalog API (`laibcatalog.co.il`) plus HTTP download.

Three chains is enough to ask “which chain is cheapest?” including
two-chain products and three-way ties. Two chains would only support a
pairwise comparison. More than three would add extractors and storage
without changing the analysis questions.

The mix is intentional: a full-service chain, a discounter, and a
third national chain, each with a different download transport.

### How to extract

Use the **official published files**, not scraped storefront HTML or
unofficial APIs for shelf prices.

- **Chain-specific extract.** Each chain has its own downloader for
  PriceFull, Stores, and PromoFull.
- **Shared parse and load.** All three publish the same PriceFull XML
  item schema, so one parser and one loader serve every chain.
- **Latest snapshot per store** is what the analytical layer uses
  (median price per chain). Full history stays in the local database.
- **CLI selection** is `python -m src.etl --chain … --extract …`.
  Development runs cap pages/files. `--full` loads without those caps.

| Chain | Transport | Source |
|-------|-----------|--------|
| Shufersal | HTTP HTML listing → file download | `prices.shufersal.co.il` |
| Rami Levy | FTP (Cerberus published prices) | `url.retail.publishedprices.co.il` |
| Victory | HTTP JSON catalog → file download | `laibcatalog.co.il` |

## Why these three, not others

- They are large enough that many `item_code` values overlap, which is
  required for exact-product comparison.
- They occupy different price positions, so category-level “who is
  cheaper?” questions are meaningful.
- They cover the three common Israeli publish transports (HTTP listing,
  FTP, catalog API), which is enough to prove the ETL design.
- Other chains (for example Osher Ad, Carrefour, Yochananof) also
  publish files. They are out of scope unless the analysis later needs
  them.

## Rejected alternatives

- **One chain.** No cross-chain comparison.
- **Two chains.** A comparison is possible, but the cheapest-chain
  table and tie logic are less interesting, and overlap is thinner.
- **Every publishing chain.** Too much extract/storage work for a
  portfolio analysis project.
- **Scrape each chain’s e-commerce site.** Fragile, not the regulated
  source, and harder to treat as official prices.
- **Buy a commercial grocery API.** Unnecessary when the statutory
  files exist and are the project’s data-engineering story.
- **A separate pipeline script per chain for parse/load.** That is
  what ADR 0001 removed. Only download transport should differ.

## Consequences

- `grocery.price_comparison` has Shufersal, Rami Levy, and Victory
  price columns. A missing chain is `NULL` (product in two chains, not
  three).
- Adding a fourth chain is an extractor plus columns/joins in the
  analytical tables. Parse/load should not be copied.
- Analysis of “the Israeli grocery market” is limited to these three
  chains. Results should not be stated as covering all retailers.
- Local storage and ETL time are bounded by three PriceFull/Stores/
  PromoFull sources, which keeps the local database usable.
