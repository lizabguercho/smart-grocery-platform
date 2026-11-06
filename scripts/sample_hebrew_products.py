"""Print a random sample of Hebrew names from grocery.products.

Read-only. Uses the shared analytical database (REMOTE_DB_* in .env).
The same sampler feeds scripts/translate_product_names.py --sample, which
still opens the local ETL database itself.

  PYTHONPATH=. uv run python scripts/sample_hebrew_products.py --limit 20
"""

from __future__ import annotations

import argparse
import csv
import sys

from src.database_loader.connection import get_remote_connection
from src.product_translation.config import SAMPLE_BATCH_SIZE
from src.product_translation.sampling import sample_hebrew_products


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a random sample of Hebrew grocery.products names."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=SAMPLE_BATCH_SIZE,
        help=f"How many names to draw (default {SAMPLE_BATCH_SIZE}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        with get_remote_connection() as connection:
            products = sample_hebrew_products(connection, args.limit)
    except Exception as error:
        print(f"Sample failed: {error}", file=sys.stderr)
        return 1

    writer = csv.writer(sys.stdout)
    writer.writerow(["item_code", "item_name"])
    for product in products:
        writer.writerow([product.item_code, product.item_name])
    print(f"Sampled {len(products)} product(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
