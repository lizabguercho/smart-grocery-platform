"""Tokenize 3 labeled products with AlephBERT. Does not train a model.

  PYTHONPATH=. .venv/bin/python -u scripts/demo_alephbert_tokenizer.py
"""

from __future__ import annotations

import pandas as pd

from src.database_loader.connection import get_connection
from src.product_classification.comparable_labels import DEFAULT_COMBINED_CSV_PATH
from src.product_classification.transformer_classifier import (
    print_alephbert_tokenizer_demo,
    texts_from_frame,
)

SAMPLE_COUNT = 3


def load_three_labeled_products() -> pd.DataFrame:
    combined = pd.read_csv(DEFAULT_COMBINED_CSV_PATH, dtype=str)
    labeled = combined[combined["category"].fillna("").str.strip() != ""]
    sample_codes = labeled["item_code"].head(SAMPLE_COUNT).tolist()
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.item_code::text,
                    COALESCE(p.item_name, ''),
                    p.manufacture_name
                FROM grocery.products AS p
                WHERE p.item_code::text = ANY(%s)
                """,
                (sample_codes,),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()
    by_code = {row[0]: row for row in rows}
    ordered = [by_code[code] for code in sample_codes if code in by_code]
    return pd.DataFrame(
        ordered,
        columns=["item_code", "item_name", "manufacture_name"],
    )


def main() -> None:
    sample = load_three_labeled_products()
    texts = texts_from_frame(sample)
    print_alephbert_tokenizer_demo(texts)


if __name__ == "__main__":
    main()
