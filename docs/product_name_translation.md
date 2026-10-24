# Hebrew → English product-name translation

Related: [Documentation map](README.md) ·
[Getting started](getting-started.md) ·
[Comparability audit](comparability_audit.md) ·
[Client-server architecture](client-server-architecture.md)

Fill `grocery.products.item_name_en` from the Hebrew `item_name` that
ETL already stores. The Hebrew name is **never** changed. English is
written only to `item_name_en`.

This is a **local** batch job against the ETL database (`DB_*` in
`.env`). It does not touch the remote analytical database.

---

## Why it exists

Official chain files ship Hebrew (or mixed) shelf names. English names
help dashboards, the chat agent, and anyone reading CSVs without Hebrew
fluency. A small local instruct model is enough for short supermarket
labels; the job is designed so one bad name does not stop the batch,
and each successful write is committed immediately.

---

## Running it

Install the optional model stack once (~ multi-GB download on first
run; weights land in the Hugging Face cache):

```bash
uv sync --group transformers
```

Then, from the repo root, with local PostgreSQL and `DB_*` configured:

```bash
# Recommended: random Hebrew sample (default 100), overwrites item_name_en
# for those barcodes only, writes a review CSV
PYTHONPATH=. uv run --group transformers python -u scripts/translate_product_names.py --sample 100

# Fill empty item_name_en only (does not overwrite existing English)
PYTHONPATH=. uv run --group transformers python -u scripts/translate_product_names.py --new-only

# Re-run rows that fail automatic quality flags (default batch of 20)
PYTHONPATH=. uv run --group transformers python -u scripts/translate_product_names.py --retry-failed
```

Unit tests never load the model or open PostgreSQL:

```bash
uv run pytest test/unit/test_product_name_translation.py
```

If the column is missing on an older database, the job runs
`ADD COLUMN IF NOT EXISTS` (same idea as `sql/08_add_item_name_en.sql`).
Current `sql/02_create_tables.sql` already includes `item_name_en`.

---

## Modes

| Flag | Selects | Writes | CSV output |
|---|---|---|---|
| `--sample N` (default when no other flag) | `N` random Hebrew `item_name` rows | Overwrites `item_name_en` for those rows | `data/processed/product_name_translations_sample.csv` |
| `--new-only` | Up to `TEST_BATCH_SIZE` (100) rows with empty `item_name_en` | Inserts only when still empty | — |
| `--retry-failed` | Up to `RETRY_FAILED_BATCH_SIZE` (20) translated rows that fail quality flags | Overwrites `item_name_en` | `data/processed/translation_failed_retries.csv` |

All three modes skip fee / voucher / pickup name phrases (see
[Exclusions](#exclusions) below).

---

## Layout

```text
scripts/translate_product_names.py   CLI entry
src/product_translation/
  config.py           model id, batch sizes, system prompt
  name_translator.py  Qwen wrapper + output cleaning
  repository.py       SQL read/write for item_name_en
  job.py              fetch → translate → save / retry
  quality.py          cheap automatic failure flags
  exclusions.py       names that are not grocery SKUs
```

```text
grocery.products.item_name  ──►  QwenProductNameTranslator  ──►  item_name_en
         │                              │
         │                              └── clean_translation()
         └── never updated
```

| Piece | Role |
|---|---|
| `QwenProductNameTranslator` | Loads `Qwen/Qwen2.5-1.5B-Instruct` once; skips the model when the name has no Hebrew letters |
| `ProductTranslationRepository` | Ensures the column, fetches batches, saves or overwrites English |
| `ProductNameTranslationJob` | Orchestrates sample / new-only / retry; continues after per-row failures |
| `quality.py` | Heuristic flags for leftover Hebrew, dropped/invented numbers, filler words, dairy hallucination, etc. |
| `exclusions.py` | Substrings that mark delivery fees, returns, Cibus/Ten Bis lines, and similar |

Protocols in `job.py` (`TranslatesProductNames`, `StoresProductTranslations`)
keep unit tests on fakes so CI never downloads weights.

---

## Prompt and cleaning

The system prompt (in `config.py`) asks for a **literal** supermarket
translation: no invented brands, countries, or units; unknown brands are
transliterated; numbers and percentages must be copied; output is the
name only.

Models still sometimes wrap the answer in quotes or a label like
`English:`. `clean_translation()` keeps the first non-empty line and
strips those wrappers.

---

## Quality flags

`failure_reasons()` / `is_failed_translation()` do **not** prove a name
is correct. They only catch failures this prompt cares about, for
example:

| Flag | Meaning |
|---|---|
| `empty_english` | Blank after cleaning |
| `hebrew_left_in_english` | Hebrew letters still in `item_name_en` |
| `missing_numbers` / `invented_numbers` | Digits or `%` dropped or added |
| `invented_words` | Filler such as “fresh”, “israel”, “premium” without Hebrew support |
| `invented_product` | Dairy English on a non-dairy Hebrew name |
| `hallucinated_words` | Known bad inventions seen on this small model |
| `too_many_extra_words` | English much longer than the Hebrew label |

`--retry-failed` re-translates flagged rows and records before/after
reasons in the retry CSV.

---

## Exclusions

Translation skips names that are not sellable grocery SKUs. The first
phrases match the comparability-audit `collision_keyword` rule in
[comparability_audit.md](comparability_audit.md); the rest cover
e-commerce fees and meal-card lines the audit list did not cover.

Examples: delivery fees (`דמי משלוח`), discounts/returns/differences,
self-pickup, Cibus (`סיבוס`), Ten Bis (`תן ביס`).

Exclusions affect **which rows are selected**. They do not delete
anything from PostgreSQL; ETL still stores those barcodes.

---

## Limits

- **Local laptop model.** `Qwen2.5-1.5B-Instruct` is instruction-tuned
  and small enough for short names; larger Qwen ids can be swapped in
  `config.QWEN_MODEL_ID`.
- **Not ground truth.** English names are generated; quality flags are
  heuristics. Spot-check sample CSVs before trusting a large fill.
- **Local DB only.** Uses `get_connection()` / `DB_*`, not
  `REMOTE_DB_*`. Syncing `item_name_en` to the remote analytical
  database is a separate step if needed.
- **Optional dependency.** Everyday `uv sync` / pytest does not install
  `transformers` / `torch`; use `--group transformers` for the script.
- **iCloud / HF import.** `skip_slow_packages_distributions()` avoids a
  hung `import transformers` when `.venv` lives under iCloud Documents
  (dataless stubs). See the comment in `name_translator.py`.

---

## Data artifacts

These CSVs are gitignored under `data/processed/`:

| Path | What it is |
|---|---|
| `product_name_translations_sample.csv` | Latest `--sample` run: `item_code`, `item_name`, `item_name_en` |
| `translation_failed_retries.csv` | Latest `--retry-failed` run: before/after English and quality reasons |
