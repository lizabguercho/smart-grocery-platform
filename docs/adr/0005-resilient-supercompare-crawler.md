# 0005. Resilient SuperCompare crawler

## Status

Accepted

Related: [supercompare_labeling.md](../supercompare_labeling.md) ·
[ADR 0004](0004-product-categorization-and-training-sample.md)

## Context

The first SuperCompare crawler used module-level functions, issued one
request per page without retries, kept the complete crawl in memory, and
wrote one CSV only after every request succeeded.

A transient TLS failure on one page therefore discarded all progress from
the run. Full taxonomy crawls make enough requests that transport failures,
HTTP rate limits, and server errors must be expected.

Raw SuperCompare memberships are silver labels. They are not accepted
classifications and cannot be written directly to
`grocery.product_classification`, whose primary key permits only one label
per barcode.

## Decision

Use three collaborating objects:

1. `SuperCompareClient` owns a reusable HTTP session, response validation,
   sequential rate limiting, and bounded retries.
2. `SuperCompareBatchStore` writes page checkpoints and reports atomically,
   validates cached pages, and builds the processed CSV atomically.
3. `SuperCompareCrawler` owns workflow order, resume behavior, failure
   isolation, and the final summary.

One API page is one persistence batch. Checkpoints are stored under:

```text
data/raw/supercompare/<category>/<subcategory>/page_XXXX.json
```

The crawler retries transport failures, HTTP 429, and selected HTTP 5xx
responses up to five attempts. Requests remain sequential and at least one
second apart. Retry waits use bounded exponential backoff with jitter and
honor a bounded `Retry-After` response header. TLS verification is never
disabled.

If retries are exhausted, the failed page is recorded and other independent
pages continue. The run exits unsuccessfully, but completed checkpoints
remain available for the next resumable run. An incomplete run never
replaces the last complete `supercompare_products.csv`.

The supported launcher is:

```bash
uv run python -m src.product_classification.supercompare
```

Library modules emit records through Python `logging`; only the CLI configures
console and rotating-file handlers.

## Consequences

- A failed full crawl resumes from valid page checkpoints instead of starting
  over.
- Rebuilding the CSV from checkpoints prevents duplicate appends while
  retaining a barcode that intentionally appears in multiple category
  endpoints.
- Raw crawl artifacts remain local and gitignored. Promotion into the remote
  classification table remains a separate reviewed step.
- Retry, storage, orchestration, and CLI behavior can be unit tested without
  live HTTP or PostgreSQL.
- A permanently invalid CA bundle still fails. Retries address transient
  failures; they do not replace certificate verification or environment
  repair.
