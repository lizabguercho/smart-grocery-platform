"""Checks for the TF-IDF + Linear SVM review helpers.

These tests use a tiny toy model. They do not refit the grocery classifier.
"""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC

from src.product_classification.category_classifier import (
    AUDIT_COLUMNS,
    build_classification_audit,
    inspect_category,
    lowest_confidence_per_category,
    search_products,
    svm_decision_details,
)


def test_svm_decision_details_reads_the_top_two_scores() -> None:
    texts = ["milk"] * 6 + ["cola drink"] * 6 + ["dish soap"] * 6
    labels = ["Dairy & Eggs"] * 6 + ["Beverages"] * 6 + ["Household & Cleaning"] * 6
    vectorizer = TfidfVectorizer()
    features = vectorizer.fit_transform(texts)
    model = LinearSVC(random_state=42, max_iter=2000)
    model.fit(features, labels)

    details = svm_decision_details(model, features)

    assert list(details.columns) == [
        "predicted_category",
        "second_best_category",
        "confidence",
    ]
    assert list(details["predicted_category"]) == list(model.predict(features))
    assert (details["predicted_category"] != details["second_best_category"]).all()
    # The winning decision_function value can sit outside 0..1. It is not a probability.
    scores = model.decision_function(features)
    assert list(details["confidence"]) == list(scores.max(axis=1))


def test_helpers_find_dairy_xl_and_the_least_sure_rows() -> None:
    scored = pd.DataFrame(
        {
            "item_code": ["1", "2", "3", "4"],
            "item_name": ["XL energy", "milk", "xl cola", "bread"],
            "manufacture_name": ["A", "B", "C", "D"],
            "predicted_category": [
                "Dairy & Eggs",
                "Dairy & Eggs",
                "Beverages",
                "Bakery",
            ],
            "second_best_category": [
                "Beverages",
                "Pantry & Cooking",
                "Dairy & Eggs",
                "Snacks & Sweets",
            ],
            "confidence": [0.2, 1.5, 0.1, 3.0],
        }
    )

    assert list(inspect_category(scored, "Dairy")["item_code"]) == ["1", "2"]
    assert list(search_products(scored, "XL")["item_code"]) == ["1", "3"]
    xl_as_dairy = inspect_category(search_products(scored, "XL"), "Dairy")
    assert list(xl_as_dairy["item_code"]) == ["1"]
    assert xl_as_dairy.iloc[0]["second_best_category"] == "Beverages"

    lowest = lowest_confidence_per_category(scored, n=1)
    assert set(lowest["item_code"]) == {"1", "3", "4"}

    audit = build_classification_audit(scored, n=1)
    assert list(audit.columns) == AUDIT_COLUMNS
    assert list(audit["review_status"]) == ["", "", ""]
    assert list(audit["correct_category"]) == ["", "", ""]
