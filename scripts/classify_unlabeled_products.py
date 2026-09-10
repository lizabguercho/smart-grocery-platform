"""Classify unlabeled comparable products using TF-IDF + Linear SVM.

Fits the baseline model on all 5,718 SuperCompare-labeled comparable products
(with approved label corrections) and generates predictions for the remaining
9,098 comparable products.

Does not write to PostgreSQL.

Run:
  PYTHONPATH=. .venv/bin/python -u scripts/classify_unlabeled_products.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.run_category_classifier_experiments import (
    LABEL_REVIEW_PATH,
    apply_obvious_labels,
    obvious_label_overlay,
)
from src.database_loader.connection import get_connection
from src.product_classification.category_classifier import (
    MODEL_LINEAR_SVM,
    build_feature_text,
    fit_tfidf_and_model,
    labeled_frame_from_rows,
)
from src.product_classification.comparable_labels import (
    join_to_comparable,
    load_unique_products,
)
from src.product_classification.supercompare.config import DEFAULT_PRODUCTS_PATH

OUTPUT_DIR = Path("data/processed")
OUTPUT_PATH = OUTPUT_DIR / "unlabeled_product_predictions.csv"
CLASSIFICATION_METHOD = "tfidf_linear_svm"


def fetch_comparable_products_from_db() -> list[tuple[str, str, str | None]]:
    """Fetch all comparable products and their metadata from the local database."""
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
            return cursor.fetchall()
    finally:
        connection.close()


def prepare_labeled_and_unlabeled_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load SuperCompare labels and partition comparable products into labeled and unlabeled sets."""
    print("Reading SuperCompare labels from CSV...", flush=True)
    unique_products, dropped = load_unique_products(DEFAULT_PRODUCTS_PATH)
    print(
        f"Unique SuperCompare barcodes: {len(unique_products)} "
        f"(dropped {dropped} duplicate rows)",
        flush=True,
    )

    print("Loading comparable products from local DB...", flush=True)
    comparable_rows = fetch_comparable_products_from_db()
    print(f"Total comparable products in database: {len(comparable_rows)}", flush=True)

    comparable_codes = [row[0] for row in comparable_rows]
    matched = join_to_comparable(unique_products, comparable_codes)
    labels = {product.item_code: product.main_category for product in matched}

    labeled_rows = []
    unlabeled_rows = []
    for item_code, item_name, manufacture_name in comparable_rows:
        category = labels.get(item_code)
        if category is not None:
            labeled_rows.append(
                {
                    "item_code": item_code,
                    "item_name": item_name,
                    "manufacture_name": manufacture_name,
                    "category": category,
                }
            )
        else:
            unlabeled_rows.append(
                {
                    "item_code": item_code,
                    "item_name": item_name,
                    "manufacture_name": manufacture_name,
                }
            )

    labeled_frame = labeled_frame_from_rows(labeled_rows)
    print(f"Labeled products: {len(labeled_frame)}", flush=True)

    if LABEL_REVIEW_PATH.exists():
        overlay = obvious_label_overlay(LABEL_REVIEW_PATH)
        print(f"Applying {len(overlay)} approved label corrections...", flush=True)
        labeled_frame = apply_obvious_labels(labeled_frame, overlay)

    unlabeled_frame = pd.DataFrame(unlabeled_rows)
    unlabeled_frame["item_code"] = unlabeled_frame["item_code"].astype(str)
    unlabeled_frame["item_name"] = unlabeled_frame["item_name"].fillna("").astype(str)
    print(f"Unlabeled products to predict: {len(unlabeled_frame)}", flush=True)

    return labeled_frame, unlabeled_frame


def classify_unlabeled_products(
    labeled_frame: pd.DataFrame, unlabeled_frame: pd.DataFrame
) -> pd.DataFrame:
    """Fit TF-IDF + Linear SVM on all labeled products and predict categories for unlabeled."""
    print(
        f"\nFitting TF-IDF + Linear SVM on all {len(labeled_frame)} labeled products...",
        flush=True,
    )

    train_texts = [
        build_feature_text(
            row.item_name,
            row.manufacture_name,
            include_manufacturer=True,
        )
        for row in labeled_frame.itertuples(index=False)
    ]
    y_train = labeled_frame["category"]

    vectorizer, model = fit_tfidf_and_model(
        train_texts,
        y_train,
        MODEL_LINEAR_SVM,
    )

    print(
        f"Generating predictions for {len(unlabeled_frame)} unlabeled products...",
        flush=True,
    )
    unlabeled_texts = [
        build_feature_text(
            row.item_name,
            row.manufacture_name,
            include_manufacturer=True,
        )
        for row in unlabeled_frame.itertuples(index=False)
    ]
    x_unlabeled = vectorizer.transform(unlabeled_texts)
    predictions = model.predict(x_unlabeled)

    result_df = pd.DataFrame(
        {
            "item_code": unlabeled_frame["item_code"],
            "item_name": unlabeled_frame["item_name"],
            "manufacture_name": unlabeled_frame["manufacture_name"],
            "predicted_category": predictions,
            "classification_method": CLASSIFICATION_METHOD,
        }
    )
    return result_df


def validate_and_print_summary(df: pd.DataFrame, allowed_categories: set[str]) -> None:
    """Validate prediction constraints and print category distribution."""
    total = len(df)
    n_dupes = int(df["item_code"].duplicated().sum())
    n_missing = int(
        df["predicted_category"].isna().sum()
        + (df["predicted_category"].astype(str).str.strip() == "").sum()
    )
    canonical_set = allowed_categories
    invalid_cats = set(df["predicted_category"]) - canonical_set

    print(f"\n--- Validation Checks ---", flush=True)
    print(f"Total predictions:                 {total}", flush=True)
    print(f"Duplicate item_code count:         {n_dupes}", flush=True)
    print(f"Missing predicted categories:      {n_missing}", flush=True)
    print(f"Unknown predicted category values: {len(invalid_cats)}", flush=True)

    # Required assertions before saving
    assert n_dupes == 0, f"Validation error: found {n_dupes} duplicate item_code values."
    assert n_missing == 0, f"Validation error: found {n_missing} missing predicted categories."
    assert not invalid_cats, f"Validation error: unexpected category names {invalid_cats}."

    print("\n--- Predicted Category Distribution ---", flush=True)
    counts = df["predicted_category"].value_counts()
    print(f"{'Category':<28} {'Count':>7} {'Share':>8}", flush=True)
    print("-" * 46, flush=True)
    for category, count in counts.items():
        share = count / total * 100.0
        print(f"{category:<28} {count:>7} {share:>7.2f}%", flush=True)
    print("-" * 46, flush=True)
    print(f"{'Total':<28} {total:>7} {'100.00%':>8}", flush=True)


def main() -> None:
    labeled_frame, unlabeled_frame = prepare_labeled_and_unlabeled_data()
    predictions_df = classify_unlabeled_products(labeled_frame, unlabeled_frame)

    validate_and_print_summary(
        predictions_df,
        set(labeled_frame["category"].dropna().astype(str)),
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    print(f"\nSaved all predictions to: {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
