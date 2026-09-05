"""Classical 12-class main-category experiments on SuperCompare labels.

This module is intentionally linear: clean text, split once, TF-IDF,
fit a model, score. It does not write to the database.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

RANDOM_STATE = 42
TRAIN_FRACTION = 0.70
VALIDATION_OF_HOLD_OUT = 0.50  # 15% of all rows after a 30% hold-out

# Placeholders treated as "no manufacturer" (same idea as the completeness check).
MISSING_MANUFACTURER = frozenset(
    {
        "",
        "-",
        "--",
        "לא ידוע",
        "unknown",
        "n/a",
        "na",
        "none",
        "null",
    }
)

FEATURE_ITEM_NAME = "item_name"
FEATURE_ITEM_NAME_AND_MANUFACTURER = "item_name + manufacture_name"

MODEL_LOGISTIC_REGRESSION = "TF-IDF + Logistic Regression"
MODEL_LINEAR_SVM = "TF-IDF + Linear SVM"
MODEL_NAIVE_BAYES = "TF-IDF + Multinomial Naive Bayes"


@dataclass(frozen=True)
class ExperimentResult:
    features: str
    model_name: str
    accuracy: float
    macro_f1: float


def clean_manufacture_name(value: object) -> str:
    """Turn missing / placeholder manufacturer values into an empty string."""

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.lower() in MISSING_MANUFACTURER:
        return ""
    if text in MISSING_MANUFACTURER:
        return ""
    return text


def build_feature_text(
    item_name: object,
    manufacture_name: object,
    *,
    include_manufacturer: bool,
) -> str:
    """Build one text string per product for TF-IDF."""

    if item_name is None or (isinstance(item_name, float) and pd.isna(item_name)):
        name = ""
    else:
        name = str(item_name).strip()
    if not include_manufacturer:
        return name
    manufacturer = clean_manufacture_name(manufacture_name)
    if not manufacturer:
        return name
    return f"{name} {manufacturer}".strip()


def labeled_frame_from_rows(rows: Sequence[Mapping[str, object]]) -> pd.DataFrame:
    """Build the modeling table: one row per labeled comparable product."""

    frame = pd.DataFrame(list(rows))
    required = {"item_code", "item_name", "manufacture_name", "category"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Labeled data is missing columns: {sorted(missing)}")
    frame = frame.copy()
    frame["item_code"] = frame["item_code"].astype(str)
    frame["item_name"] = frame["item_name"].fillna("").astype(str)
    frame["manufacture_name"] = frame["manufacture_name"].map(clean_manufacture_name)
    frame["category"] = frame["category"].astype(str)
    frame = frame.drop_duplicates(subset=["item_code"], keep="first")
    return frame.reset_index(drop=True)


def stratified_train_val_test(
    frame: pd.DataFrame,
    *,
    random_state: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """70% train / 15% validation / 15% test, same category mix in each split."""

    if "category" not in frame.columns:
        raise ValueError("frame must include a category column")
    train, hold_out = train_test_split(
        frame,
        test_size=1.0 - TRAIN_FRACTION,
        stratify=frame["category"],
        random_state=random_state,
    )
    validation, test = train_test_split(
        hold_out,
        test_size=VALIDATION_OF_HOLD_OUT,
        stratify=hold_out["category"],
        random_state=random_state,
    )
    return (
        train.reset_index(drop=True),
        validation.reset_index(drop=True),
        test.reset_index(drop=True),
    )


def category_counts_table(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> pd.DataFrame:
    """One row per category with counts in each split."""

    counts = pd.DataFrame(
        {
            "train": train["category"].value_counts(),
            "validation": validation["category"].value_counts(),
            "test": test["category"].value_counts(),
        }
    ).fillna(0).astype(int)
    counts["total"] = counts["train"] + counts["validation"] + counts["test"]
    return counts.sort_values("total", ascending=False)


def make_model(model_name: str):
    """Simple sklearn models; no hyperparameter search."""

    if model_name == MODEL_LOGISTIC_REGRESSION:
        return LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    if model_name == MODEL_LINEAR_SVM:
        return LinearSVC(random_state=RANDOM_STATE, max_iter=2000)
    if model_name == MODEL_NAIVE_BAYES:
        return MultinomialNB()
    raise ValueError(f"Unknown model: {model_name}")


def fit_tfidf_and_model(
    train_text: Sequence[str],
    y_train: Sequence[str],
    model_name: str,
) -> tuple[TfidfVectorizer, object]:
    """Learn TF-IDF vocabulary on train only, then fit the classifier."""

    vectorizer = TfidfVectorizer()
    x_train = vectorizer.fit_transform(train_text)
    model = make_model(model_name)
    model.fit(x_train, y_train)
    return vectorizer, model


def score_predictions(y_true: Sequence[str], y_pred: Sequence[str]) -> tuple[float, float]:
    accuracy = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    return accuracy, macro_f1


def run_experiment(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    *,
    include_manufacturer: bool,
    model_name: str,
) -> ExperimentResult:
    """Train on Train, score on Validation. Never looks at Test."""

    feature_label = (
        FEATURE_ITEM_NAME_AND_MANUFACTURER
        if include_manufacturer
        else FEATURE_ITEM_NAME
    )
    train_text = [
        build_feature_text(
            row.item_name,
            row.manufacture_name,
            include_manufacturer=include_manufacturer,
        )
        for row in train.itertuples(index=False)
    ]
    val_text = [
        build_feature_text(
            row.item_name,
            row.manufacture_name,
            include_manufacturer=include_manufacturer,
        )
        for row in validation.itertuples(index=False)
    ]
    vectorizer, model = fit_tfidf_and_model(train_text, train["category"], model_name)
    y_pred = model.predict(vectorizer.transform(val_text))
    accuracy, macro_f1 = score_predictions(validation["category"], y_pred)
    return ExperimentResult(
        features=feature_label,
        model_name=model_name,
        accuracy=accuracy,
        macro_f1=macro_f1,
    )


def evaluate_winner_on_test(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    include_manufacturer: bool,
    model_name: str,
) -> tuple[float, float, str, pd.DataFrame, Sequence[str]]:
    """Refit the chosen setup on Train only, then score the untouched Test set."""

    train_text = [
        build_feature_text(
            row.item_name,
            row.manufacture_name,
            include_manufacturer=include_manufacturer,
        )
        for row in train.itertuples(index=False)
    ]
    test_text = [
        build_feature_text(
            row.item_name,
            row.manufacture_name,
            include_manufacturer=include_manufacturer,
        )
        for row in test.itertuples(index=False)
    ]
    vectorizer, model = fit_tfidf_and_model(train_text, train["category"], model_name)
    y_true = test["category"]
    y_pred = model.predict(vectorizer.transform(test_text))
    accuracy, macro_f1 = score_predictions(y_true, y_pred)
    labels = sorted(train["category"].unique())
    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        digits=3,
        zero_division=0,
    )
    confusion = pd.crosstab(
        pd.Series(y_true, name="true"),
        pd.Series(y_pred, name="predicted"),
        dropna=False,
    )
    confusion = confusion.reindex(index=labels, columns=labels, fill_value=0)
    return accuracy, macro_f1, report, confusion, y_pred


def misclassified_test_rows(
    test: pd.DataFrame,
    y_pred: Sequence[str],
) -> pd.DataFrame:
    """Test products whose predicted main category differs from the SuperCompare label."""

    errors = test.copy()
    errors["true_category"] = errors["category"].astype(str)
    errors["predicted_category"] = list(y_pred)
    errors = errors[errors["true_category"] != errors["predicted_category"]]
    return errors[
        [
            "item_code",
            "item_name",
            "manufacture_name",
            "true_category",
            "predicted_category",
        ]
    ].reset_index(drop=True)


def select_winner(results: Sequence[ExperimentResult]) -> ExperimentResult:
    """Highest validation Macro F1; accuracy breaks ties."""

    return max(results, key=lambda row: (row.macro_f1, row.accuracy, row.model_name))
