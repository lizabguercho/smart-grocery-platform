"""List Test-set mistakes for the winning TF-IDF + Linear SVM model.

Uses the same stratified split and winner features as the experiments.
Does not change hyperparameters and does not write to the database.

  PYTHONPATH=. .venv/bin/python3 -u scripts/analyze_classifier_test_errors.py
"""

from __future__ import annotations

print("starting", flush=True)

from pathlib import Path

print("imports: sklearn helpers via category_classifier...", flush=True)

from src.product_classification.category_classifier import (
    MODEL_LINEAR_SVM,
    evaluate_winner_on_test,
    labeled_frame_from_rows,
    misclassified_test_rows,
    stratified_train_val_test,
)

print("imports: database + SuperCompare...", flush=True)

from src.database_loader.connection import get_connection
from src.product_classification.comparable_labels import (
    effective_main_category,
    join_to_comparable,
    load_unique_products,
)
from src.product_classification.supercompare.config import DEFAULT_PRODUCTS_PATH

OUTPUT_DIR = Path("data/processed")
ERRORS_PATH = OUTPUT_DIR / "classifier_test_errors.csv"
PAIR_COUNTS_PATH = OUTPUT_DIR / "classifier_test_error_pairs.csv"


def load_labeled_comparable_products():
    print("Reading SuperCompare labels...", flush=True)
    unique_products, dropped = load_unique_products(DEFAULT_PRODUCTS_PATH)
    print(
        f"Unique SuperCompare barcodes: {len(unique_products)} "
        f"(dropped {dropped} duplicate rows)",
        flush=True,
    )
    print("Loading comparable products from local DB...", flush=True)
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    pc.item_code::text,
                    COALESCE(p.item_name, ''),
                    p.manufacture_name
                FROM grocery.price_comparison AS pc
                INNER JOIN grocery.products AS p
                    ON p.item_code = pc.item_code
                ORDER BY pc.item_code
                """
            )
            comparable_rows = cursor.fetchall()
    finally:
        connection.close()

    comparable_codes = [row[0] for row in comparable_rows]
    matched = join_to_comparable(unique_products, comparable_codes)
    labels = {
        product.item_code: effective_main_category(
            product.item_code, product.main_category
        )
        for product in matched
    }
    rows = []
    for item_code, item_name, manufacture_name in comparable_rows:
        category = labels.get(item_code)
        if category is None:
            continue
        rows.append(
            {
                "item_code": item_code,
                "item_name": item_name,
                "manufacture_name": manufacture_name,
                "category": category,
            }
        )
    return labeled_frame_from_rows(rows)


def main() -> None:
    frame = load_labeled_comparable_products()
    train, _validation, test = stratified_train_val_test(frame)
    print(
        f"Refitting winner on Train ({len(train)}) and scoring Test ({len(test)})...",
        flush=True,
    )
    _acc, _f1, _report, _confusion, y_pred = evaluate_winner_on_test(
        train,
        test,
        include_manufacturer=True,
        model_name=MODEL_LINEAR_SVM,
    )
    errors = misclassified_test_rows(test, y_pred)
    pairs = (
        errors.groupby(["true_category", "predicted_category"])
        .size()
        .reset_index(name="n")
        .sort_values(["n", "true_category"], ascending=[False, True])
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    errors.to_csv(ERRORS_PATH, index=False)
    pairs.to_csv(PAIR_COUNTS_PATH, index=False)
    print(f"Test products: {len(test)}", flush=True)
    print(f"Misclassified: {len(errors)} ({len(errors) / len(test) * 100:.1f}%)", flush=True)
    print("\nMost common true → predicted pairs:", flush=True)
    print(pairs.head(20).to_string(index=False), flush=True)
    print(f"\nSaved {ERRORS_PATH}", flush=True)
    print(f"Saved {PAIR_COUNTS_PATH}", flush=True)


if __name__ == "__main__":
    main()
