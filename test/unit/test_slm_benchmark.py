"""Unit tests for deterministic SLM benchmark helpers (no model download)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.slm_benchmark import BENCHMARK_VERSION
from src.slm_benchmark.build_dataset import slice_tags_for, stratified_sample_products
from src.slm_benchmark.categories import ALLOWED_CATEGORIES
from src.slm_benchmark.dataset import load_benchmark, write_benchmark_csv
from src.slm_benchmark.metrics import ScoredPrediction, compute_metrics, failure_rows
from src.slm_benchmark.parse import parse_model_output
from src.slm_benchmark.prompt import load_prompt
from src.slm_benchmark.schema import BenchmarkRow, GroceryUnderstandingPrediction


def test_allowed_categories_are_twelve() -> None:
    assert len(ALLOWED_CATEGORIES) == 12
    assert "Dairy & Eggs" in ALLOWED_CATEGORIES


def test_schema_rejects_unknown_category() -> None:
    with pytest.raises(Exception):
        GroceryUnderstandingPrediction(is_product=True, category="Tobacco")


def test_schema_rejects_category_when_not_product() -> None:
    pred = GroceryUnderstandingPrediction(
        is_product=False, category="Beverages"
    )
    cleared = pred.with_non_product_category_cleared()
    assert cleared.is_product is False
    assert cleared.category is None


def test_parse_non_product_with_category_coerces() -> None:
    result = parse_model_output(
        json.dumps(
            {
                "is_product": False,
                "category": "Fresh Produce",
                "brand": None,
                "normalized_name_en": "x",
                "quantity": 1,
                "unit": "g",
            }
        )
    )
    assert result.parse_success
    assert result.prediction is not None
    assert result.prediction.category is None


def test_parse_strips_markdown_fence() -> None:
    raw = """```json
{"is_product": true, "category": "Beverages", "brand": "Coca-Cola",
 "normalized_name_en": "Coca-Cola Zero", "quantity": 1.5, "unit": "L"}
```"""
    result = parse_model_output(raw)
    assert result.parse_success
    assert result.prediction is not None
    assert result.prediction.category == "Beverages"
    assert result.prediction.quantity == 1.5


def test_parse_malformed_json_is_failure_not_crash() -> None:
    result = parse_model_output("sorry, here is {not json")
    assert not result.parse_success
    assert result.prediction is None
    assert result.error_message


def test_parse_non_product() -> None:
    result = parse_model_output(
        json.dumps(
            {
                "is_product": False,
                "category": None,
                "brand": None,
                "normalized_name_en": None,
                "quantity": None,
                "unit": None,
            }
        )
    )
    assert result.parse_success
    assert result.prediction is not None
    assert result.prediction.is_product is False


def test_zero_shot_prompt_has_no_worked_examples() -> None:
    prompt = load_prompt("zero_shot_v1")
    assert "קוקה" not in prompt.system_text
    assert "example" not in prompt.system_text.lower()
    assert "Beverages" in prompt.system_text


def test_benchmark_load_rejects_duplicate_item_codes(tmp_path: Path) -> None:
    rows = [
        BenchmarkRow(
            benchmark_version=BENCHMARK_VERSION,
            item_code="1",
            raw_item_name="א",
            is_product=True,
            category="Baby",
        ),
        BenchmarkRow(
            benchmark_version=BENCHMARK_VERSION,
            item_code="1",
            raw_item_name="ב",
            is_product=True,
            category="Baby",
        ),
    ]
    path = tmp_path / "dup.csv"
    write_benchmark_csv(rows, path)
    with pytest.raises(ValueError, match="duplicate"):
        load_benchmark(path)


def test_stratified_sample_unique_names() -> None:
    candidates = [
        {
            "item_code": str(i),
            "raw_item_name": f"name-{i % 3}",
            "category": ALLOWED_CATEGORIES[i % 12],
            "subcategory": "x",
            "manufacture_name": "",
        }
        for i in range(60)
    ]
    # Force one category with duplicates of the same name.
    for i in range(20):
        candidates.append(
            {
                "item_code": f"dup-{i}",
                "raw_item_name": "same milk",
                "category": "Dairy & Eggs",
                "subcategory": "x",
                "manufacture_name": "",
            }
        )
    sampled = stratified_sample_products(candidates, per_category=5, seed=42)
    names = [row["raw_item_name"].casefold() for row in sampled]
    assert len(names) == len(set(names))


def test_slice_tags_non_product() -> None:
    tags = slice_tags_for("דמי משלוח אינטרנט", is_product=False)
    assert "non_product" in tags.split("|")


def test_metrics_and_errors() -> None:
    gold = BenchmarkRow(
        benchmark_version=BENCHMARK_VERSION,
        item_code="1",
        raw_item_name="חלב",
        is_product=True,
        category="Dairy & Eggs",
    )
    good = GroceryUnderstandingPrediction(
        is_product=True, category="Dairy & Eggs"
    )
    bad = GroceryUnderstandingPrediction(is_product=True, category="Beverages")
    scored = [
        ScoredPrediction(
            row=gold,
            parse_success=True,
            prediction=good,
            latency_seconds=0.1,
            raw_model_output="{}",
        ),
        ScoredPrediction(
            row=gold.model_copy(update={"item_code": "2"}),
            parse_success=True,
            prediction=bad,
            latency_seconds=0.2,
            raw_model_output="{}",
        ),
        ScoredPrediction(
            row=gold.model_copy(update={"item_code": "3"}),
            parse_success=False,
            prediction=None,
            latency_seconds=0.3,
            error_message="no_json_object_found",
            raw_model_output="oops",
        ),
    ]
    metrics = compute_metrics(scored)
    assert metrics["n"] == 3
    assert metrics["structural"]["parse_success_count"] == 2
    assert metrics["category"]["n"] == 3
    errors = failure_rows(scored)
    assert len(errors) == 2
    assert errors[0]["failed_fields"]
