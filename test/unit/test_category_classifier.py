import pandas as pd

from src.product_classification.category_classifier import (
    MODEL_LOGISTIC_REGRESSION,
    ExperimentResult,
    build_feature_text,
    category_counts_table,
    clean_manufacture_name,
    labeled_frame_from_rows,
    run_experiment,
    select_winner,
    stratified_train_val_test,
)


def test_clean_manufacture_name_turns_placeholders_into_empty() -> None:
    assert clean_manufacture_name(None) == ""
    assert clean_manufacture_name("  ") == ""
    assert clean_manufacture_name("-") == ""
    assert clean_manufacture_name("לא ידוע") == ""
    assert clean_manufacture_name("Tnuva") == "Tnuva"


def test_build_feature_text_keeps_name_only_when_asked() -> None:
    assert (
        build_feature_text("חלב 3%", "תנובה", include_manufacturer=False)
        == "חלב 3%"
    )
    assert (
        build_feature_text("חלב 3%", "תנובה", include_manufacturer=True)
        == "חלב 3% תנובה"
    )
    assert (
        build_feature_text("חלב 3%", None, include_manufacturer=True)
        == "חלב 3%"
    )


def test_stratified_split_keeps_every_category_in_each_part() -> None:
    rows = []
    categories = [f"cat_{index}" for index in range(4)]
    for category in categories:
        for item in range(20):
            rows.append(
                {
                    "item_code": f"{category}-{item}",
                    "item_name": f"product {category} {item}",
                    "manufacture_name": "Brand",
                    "category": category,
                }
            )
    frame = labeled_frame_from_rows(rows)
    train, validation, test = stratified_train_val_test(frame)
    assert len(train) + len(validation) + len(test) == 80
    assert abs(len(train) / 80 - 0.70) < 0.03
    for part in (train, validation, test):
        assert set(part["category"]) == set(categories)


def test_category_counts_table_adds_to_total() -> None:
    train = pd.DataFrame({"category": ["Dairy", "Dairy", "Snacks"]})
    validation = pd.DataFrame({"category": ["Dairy", "Snacks"]})
    test = pd.DataFrame({"category": ["Snacks"]})
    counts = category_counts_table(train, validation, test)
    assert int(counts.loc["Dairy", "total"]) == 3
    assert int(counts.loc["Snacks", "total"]) == 3


def test_run_experiment_and_winner_selection_on_tiny_data() -> None:
    rows = []
    for item in range(30):
        rows.append(
            {
                "item_code": f"milk-{item}",
                "item_name": "חלב תנובה",
                "manufacture_name": "תנובה",
                "category": "Dairy",
            }
        )
        rows.append(
            {
                "item_code": f"chips-{item}",
                "item_name": "חטיף במבה",
                "manufacture_name": "אוסם",
                "category": "Snacks",
            }
        )
    frame = labeled_frame_from_rows(rows)
    train, validation, test = stratified_train_val_test(frame)
    result = run_experiment(
        train,
        validation,
        include_manufacturer=True,
        model_name=MODEL_LOGISTIC_REGRESSION,
    )
    assert 0.0 <= result.accuracy <= 1.0
    assert 0.0 <= result.macro_f1 <= 1.0
    winner = select_winner(
        [
            ExperimentResult("item_name", "a", 0.9, 0.5),
            ExperimentResult("item_name + manufacture_name", "b", 0.8, 0.7),
        ]
    )
    assert winner.model_name == "b"
    assert len(test) > 0


def test_misclassified_test_rows_keeps_only_wrong_predictions() -> None:
    from src.product_classification.category_classifier import misclassified_test_rows

    test = pd.DataFrame(
        {
            "item_code": ["1", "2", "3"],
            "item_name": ["a", "b", "c"],
            "manufacture_name": ["x", "y", "z"],
            "category": ["Bakery", "Snacks & Sweets", "Pantry & Cooking"],
        }
    )
    errors = misclassified_test_rows(
        test, ["Bakery", "Pantry & Cooking", "Pantry & Cooking"]
    )
    assert list(errors["item_code"]) == ["2"]
    assert errors.iloc[0]["true_category"] == "Snacks & Sweets"
    assert errors.iloc[0]["predicted_category"] == "Pantry & Cooking"
