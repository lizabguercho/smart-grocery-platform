"""Run the six main-category experiments and print the results.

Loads SuperCompare labels from CSV and item_name / manufacture_name from
the local grocery.products table. Does not write to any database table.

  uv run python scripts/run_category_classifier_experiments.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.database_loader.connection import get_connection
from src.product_classification.category_classifier import (
    FEATURE_ITEM_NAME_AND_MANUFACTURER,
    MODEL_LINEAR_SVM,
    MODEL_LOGISTIC_REGRESSION,
    MODEL_NAIVE_BAYES,
    category_counts_table,
    evaluate_winner_on_test,
    labeled_frame_from_rows,
    run_experiment,
    select_winner,
    stratified_train_val_test,
)
from src.product_classification.comparable_labels import (
    effective_main_category,
    join_to_comparable,
    load_unique_products,
)
from src.product_classification.supercompare.config import DEFAULT_PRODUCTS_PATH

OUTPUT_DIR = Path("data/processed")
VALIDATION_RESULTS_PATH = OUTPUT_DIR / "classifier_validation_results.csv"
SPLIT_COUNTS_PATH = OUTPUT_DIR / "classifier_split_counts.csv"
TEST_REPORT_PATH = OUTPUT_DIR / "classifier_test_classification_report.txt"
TEST_CONFUSION_PATH = OUTPUT_DIR / "classifier_test_confusion_matrix.csv"

MODELS = (
    MODEL_LOGISTIC_REGRESSION,
    MODEL_LINEAR_SVM,
    MODEL_NAIVE_BAYES,
)


def load_labeled_comparable_products() -> tuple:
    print("Reading SuperCompare labels...", flush=True)
    unique_products, dropped = load_unique_products(DEFAULT_PRODUCTS_PATH)
    print(
        f"Unique SuperCompare barcodes: {len(unique_products)} "
        f"(dropped {dropped} duplicate rows)",
        flush=True,
    )

    print(
        "Loading comparable products and manufacture_name from local DB...", flush=True
    )
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
    print(f"Labeled comparable products: {len(labels)}", flush=True)

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
    print(f"Modeling rows: {len(frame)}", flush=True)
    print(f"Main categories: {frame['category'].nunique()}", flush=True)

    train, validation, test = stratified_train_val_test(frame)
    print(
        f"Split sizes — train {len(train)}, validation {len(validation)}, test {len(test)}",
        flush=True,
    )
    counts = category_counts_table(train, validation, test)
    print("\nCategory counts by split:", flush=True)
    print(counts.to_string(), flush=True)

    results = []
    print("\nValidation experiments (test set is not used here):", flush=True)
    for include_manufacturer in (False, True):
        for model_name in MODELS:
            result = run_experiment(
                train,
                validation,
                include_manufacturer=include_manufacturer,
                model_name=model_name,
            )
            results.append(result)
            print(
                f"  {result.features:32}  {result.model_name:36}  "
                f"acc={result.accuracy:.4f}  macro_f1={result.macro_f1:.4f}",
                flush=True,
            )

    winner = select_winner(results)
    print(
        f"\nWinner by validation Macro F1: {winner.features} + {winner.model_name} "
        f"(macro_f1={winner.macro_f1:.4f}, acc={winner.accuracy:.4f})",
        flush=True,
    )

    include_manufacturer = winner.features == FEATURE_ITEM_NAME_AND_MANUFACTURER
    test_acc, test_f1, report, confusion, _ = evaluate_winner_on_test(
        train,
        test,
        include_manufacturer=include_manufacturer,
        model_name=winner.model_name,
    )
    print("\nUntouched TEST set (winner only):", flush=True)
    print(f"  Test accuracy: {test_acc:.4f}", flush=True)
    print(f"  Test macro F1: {test_f1:.4f}", flush=True)
    print(report, flush=True)
    print("Confusion matrix (rows = true, columns = predicted):", flush=True)
    print(confusion.to_string(), flush=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    counts.to_csv(SPLIT_COUNTS_PATH)
    pd_results = pd.DataFrame(
        [
            {
                "features": row.features,
                "model": row.model_name,
                "validation_accuracy": round(row.accuracy, 4),
                "validation_macro_f1": round(row.macro_f1, 4),
            }
            for row in results
        ]
    )
    pd_results.to_csv(VALIDATION_RESULTS_PATH, index=False)
    TEST_REPORT_PATH.write_text(
        (
            f"Winner: {winner.features} + {winner.model_name}\n"
            f"Validation accuracy: {winner.accuracy:.4f}\n"
            f"Validation macro F1: {winner.macro_f1:.4f}\n"
            f"Test accuracy: {test_acc:.4f}\n"
            f"Test macro F1: {test_f1:.4f}\n\n"
            f"{report}"
        ),
        encoding="utf-8",
    )
    confusion.to_csv(TEST_CONFUSION_PATH)
    print(f"\nSaved {VALIDATION_RESULTS_PATH}", flush=True)
    print(f"Saved {SPLIT_COUNTS_PATH}", flush=True)
    print(f"Saved {TEST_REPORT_PATH}", flush=True)
    print(f"Saved {TEST_CONFUSION_PATH}", flush=True)


if __name__ == "__main__":
    main()
