"""AlephBERT token-length stats on the 5,718 labeled comparable products.

Does not train a model and does not write to any database table.

  PYTHONPATH=. .venv/bin/python -u scripts/analyze_alephbert_token_lengths.py
"""

from __future__ import annotations

LONGEST_TO_SHOW = 5
THRESHOLDS = (32, 64)


def load_labeled_comparable_products():
    """Same labeled barcodes as the classifier, with grocery name + manufacturer."""

    import pandas as pd

    from src.database_loader.connection import get_connection
    from src.product_classification.comparable_labels import DEFAULT_COMBINED_CSV_PATH

    print(f"Reading labeled barcodes from {DEFAULT_COMBINED_CSV_PATH}...", flush=True)
    combined = pd.read_csv(DEFAULT_COMBINED_CSV_PATH, dtype=str)
    labeled = combined[combined["category"].fillna("").str.strip() != ""].copy()
    labeled = labeled.drop_duplicates(subset=["item_code"], keep="first")
    sample_codes = labeled["item_code"].tolist()
    print(f"Labeled comparable products: {len(sample_codes)}", flush=True)

    print("Loading item_name and manufacture_name from local DB...", flush=True)
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
    missing = len(sample_codes) - len(ordered)
    if missing:
        print(f"Barcodes not found in grocery.products: {missing}", flush=True)
    return pd.DataFrame(
        ordered,
        columns=["item_code", "item_name", "manufacture_name"],
    )


def main() -> None:
    print("Starting token-length analysis...", flush=True)
    frame = load_labeled_comparable_products()

    from src.product_classification.transformer_classifier import (
        ALEPHBERT_MODEL_ID,
        texts_from_frame,
    )

    texts = texts_from_frame(frame)
    print(f"Texts built: {len(texts)}", flush=True)

    print(f"Loading tokenizer {ALEPHBERT_MODEL_ID}...", flush=True)
    import numpy as np
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(ALEPHBERT_MODEL_ID)
    encoded = tokenizer(texts, padding=False, truncation=False)
    lengths = np.array([len(ids) for ids in encoded["input_ids"]], dtype=int)

    n = len(lengths)
    print("Special tokens included; no padding; no truncation.", flush=True)
    print(f"minimum:         {int(lengths.min())}", flush=True)
    print(f"median:          {float(np.median(lengths)):.1f}", flush=True)
    print(f"90th percentile: {float(np.percentile(lengths, 90)):.1f}", flush=True)
    print(f"95th percentile: {float(np.percentile(lengths, 95)):.1f}", flush=True)
    print(f"99th percentile: {float(np.percentile(lengths, 99)):.1f}", flush=True)
    print(f"maximum:         {int(lengths.max())}", flush=True)

    for limit in THRESHOLDS:
        count = int((lengths > limit).sum())
        percent = 100.0 * count / n
        print(f"longer than {limit}: {count} ({percent:.2f}%)", flush=True)

    print(f"\n{LONGEST_TO_SHOW} longest product texts:", flush=True)
    order = np.argsort(lengths)[::-1][:LONGEST_TO_SHOW]
    for rank, index in enumerate(order, start=1):
        print(f"  {rank}. tokens={int(lengths[index])}  {texts[int(index)]}", flush=True)


if __name__ == "__main__":
    main()
