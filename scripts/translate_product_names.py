"""Translate real Hebrew product names from grocery.products with a local Qwen model.

The input is always item_name from the supermarket files (ETL).
item_name is never changed. English is written only to item_name_en.

Setup (once):
  uv sync --group transformers

Translate a random 100 Hebrew catalog names (recommended):
  PYTHONPATH=. uv run --group transformers python -u scripts/translate_product_names.py --sample 100

Uses the local ETL database (DB_* in .env).
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

from src.database_loader.connection import get_connection
from src.product_translation.config import (
    QWEN_MODEL_ID,
    RETRY_FAILED_BATCH_SIZE,
    SAMPLE_BATCH_SIZE,
    TEST_BATCH_SIZE,
)
from src.product_translation.job import ProductNameTranslationJob, RetryRow
from src.product_translation.name_translator import QwenProductNameTranslator
from src.product_translation.repository import ProductTranslationRepository

SAMPLE_CSV_PATH = Path("data/processed/product_name_translations_sample.csv")
RETRY_CSV_PATH = Path("data/processed/translation_failed_retries.csv")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate grocery.products.item_name into item_name_en."
    )
    parser.add_argument(
        "--sample",
        type=int,
        metavar="N",
        default=None,
        help=(
            "Translate N random Hebrew item_name values from grocery.products "
            "(default 100). Skips delivery/pickup/voucher name phrases. "
            "Overwrites item_name_en for those rows only."
        ),
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Re-translate rows whose current English name fails automatic quality flags.",
    )
    parser.add_argument(
        "--new-only",
        action="store_true",
        help=f"Translate up to {TEST_BATCH_SIZE} products that still have empty item_name_en.",
    )
    return parser.parse_args(argv)


def write_sample_csv(rows: list[RetryRow], path: Path = SAMPLE_CSV_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["item_code", "item_name", "item_name_en"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "item_code": row.item_code,
                    "item_name": row.item_name,
                    "item_name_en": row.item_name_en_after,
                }
            )
    logging.info("Wrote %s row(s) to %s", len(rows), path)


def write_retry_csv(rows: list[RetryRow], path: Path = RETRY_CSV_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "item_code",
                "item_name",
                "item_name_en_before",
                "item_name_en_after",
                "reasons_before",
                "reasons_after",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "item_code": row.item_code,
                    "item_name": row.item_name,
                    "item_name_en_before": row.item_name_en_before,
                    "item_name_en_after": row.item_name_en_after,
                    "reasons_before": row.reasons_before,
                    "reasons_after": row.reasons_after,
                }
            )
    logging.info("Wrote %s retry row(s) to %s", len(rows), path)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    sample_size = args.sample if args.sample is not None else SAMPLE_BATCH_SIZE

    translator = QwenProductNameTranslator()
    try:
        with get_connection() as connection:
            job = ProductNameTranslationJob(
                repository=ProductTranslationRepository(connection),
                translator=translator,
            )
            if args.retry_failed:
                logging.info(
                    "Retrying up to %s flagged names with %s",
                    RETRY_FAILED_BATCH_SIZE,
                    QWEN_MODEL_ID,
                )
                summary, retries = job.retry_failed(limit=RETRY_FAILED_BATCH_SIZE)
                write_retry_csv(retries)
            elif args.new_only:
                logging.info(
                    "Translating up to %s products with empty item_name_en using %s",
                    TEST_BATCH_SIZE,
                    QWEN_MODEL_ID,
                )
                summary = job.run(limit=TEST_BATCH_SIZE)
            else:
                logging.info(
                    "Translating %s random Hebrew item_name values with %s",
                    sample_size,
                    QWEN_MODEL_ID,
                )
                summary, sample_rows = job.run_hebrew_sample(limit=sample_size)
                write_sample_csv(sample_rows)
    except Exception:
        logging.exception("Translation job stopped because of a database or setup error.")
        return 1

    if summary.attempted == 0:
        logging.info("No matching products were found in grocery.products.")
    return 0 if summary.skipped_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
