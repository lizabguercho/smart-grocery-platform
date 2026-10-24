"""Unit tests for v2 translation gold / evaluation helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.slm_benchmark.annotation_io import (
    rows_from_v1,
    write_annotations,
    write_gold_csv,
    load_annotations,
    load_gold,
)
from src.slm_benchmark.annotation_schema import (
    AnnotationRow,
    AnnotationStatus,
    CandidateSkuFields,
)
from src.slm_benchmark.eval_translation import evaluate, write_translation_errors
from src.slm_benchmark.freeze_gold_v2 import REVIEWED
from src.slm_benchmark.normalize import (
    extract_percent_from_text,
    normalize_unit,
    null_aware_str_match,
    quantities_match,
    units_match,
)
from src.slm_benchmark.schema import BenchmarkRow
from src.slm_benchmark import BENCHMARK_VERSION


def test_normalize_unit_aliases() -> None:
    assert normalize_unit("גרם") == "g"
    assert normalize_unit("Grm") == "g"
    assert normalize_unit("ml") == "mL"
    assert normalize_unit('מ"ל') == "mL"
    assert normalize_unit("liter") == "L"
    assert normalize_unit(None) is None


def test_quantities_match() -> None:
    assert quantities_match(150, 150.0)
    assert quantities_match(None, None)
    assert not quantities_match(150, None)
    assert not quantities_match(150, 151)


def test_null_aware_str_match() -> None:
    assert null_aware_str_match(None, None)
    assert null_aware_str_match("Arla", "arla")
    assert not null_aware_str_match("Arla", None)


def test_extract_percent() -> None:
    assert extract_percent_from_text("חלב 2% 1ל") == 2.0


def test_accept_candidates_never_implied_by_apply() -> None:
    row = AnnotationRow(
        item_code="1",
        raw_item_name="אגוז קשיו קלוי ענק 150 גרם",
        is_product=True,
    )
    row.apply_candidates(
        CandidateSkuFields(
            name_en="Jumbo Roasted Cashews 150 g",
            brand=None,
            product_type="cashews",
            variant="jumbo roasted",
            quantity=150,
            unit="g",
        ),
        model_id="openai-chat:gpt-4o-mini",
    )
    assert row.annotation_status == AnnotationStatus.UNREVIEWED
    assert row.gold_name_en is None
    row.accept_candidates()
    assert row.annotation_status == AnnotationStatus.ACCEPTED
    assert row.gold_name_en == "Jumbo Roasted Cashews 150 g"


def test_rows_from_v1_preserve_codes() -> None:
    v1 = [
        BenchmarkRow(
            benchmark_version=BENCHMARK_VERSION,
            item_code="7290117906422",
            raw_item_name="אגוז קשיו קלוי ענק 150 גרם",
            is_product=True,
            category="Snacks & Sweets",
        ),
        BenchmarkRow(
            benchmark_version=BENCHMARK_VERSION,
            item_code="np-001",
            raw_item_name="דמי משלוח",
            is_product=False,
        ),
    ]
    rows = rows_from_v1(v1)
    assert [r.item_code for r in rows] == ["7290117906422", "np-001"]
    assert all(r.annotation_status == AnnotationStatus.UNREVIEWED for r in rows)


def test_freeze_filters_to_reviewed_only(tmp_path: Path) -> None:
    rows = [
        AnnotationRow(
            item_code="1",
            raw_item_name="חלב",
            is_product=True,
            candidate_name_en="Milk",
            gold_name_en="Milk",
            gold_quantity=1,
            gold_unit="L",
            annotation_status=AnnotationStatus.ACCEPTED,
        ),
        AnnotationRow(
            item_code="2",
            raw_item_name="דמי משלוח",
            is_product=False,
            annotation_status=AnnotationStatus.EXCLUDED,
        ),
        AnnotationRow(
            item_code="3",
            raw_item_name="לחם",
            is_product=True,
            annotation_status=AnnotationStatus.UNREVIEWED,
        ),
    ]
    gold = [row for row in rows if row.annotation_status in REVIEWED]
    path = tmp_path / "gold.csv"
    write_gold_csv(gold, path)
    loaded = load_gold(path)
    assert len(loaded) == 1
    assert loaded[0].item_code == "1"
    assert loaded[0].gold_name_en == "Milk"


def test_annotation_roundtrip_csv(tmp_path: Path) -> None:
    row = AnnotationRow(
        item_code="1",
        raw_item_name="x",
        is_product=True,
        candidate_name_en="Cashews 150 g",
        candidate_quantity=150.0,
        candidate_unit="g",
    )
    path = tmp_path / "ann.csv"
    write_annotations([row], path)
    loaded = load_annotations(path)
    assert loaded[0].candidate_name_en == "Cashews 150 g"
    assert loaded[0].candidate_quantity == 150.0
    assert loaded[0].gold_name_en is None


def test_evaluate_layers_join_and_metrics() -> None:
    gold = [
        AnnotationRow(
            item_code="7290117906422",
            raw_item_name="אגוז קשיו קלוי ענק 150 גרם",
            is_product=True,
            category="Snacks & Sweets",
            gold_name_en="Jumbo Roasted Cashews 150 g",
            gold_brand=None,
            gold_product_type="cashews",
            gold_variant="jumbo roasted",
            gold_quantity=150,
            gold_unit="g",
            annotation_status=AnnotationStatus.ACCEPTED,
        ),
        AnnotationRow(
            item_code="np-026",
            raw_item_name="דמי משלוח הזמנה",
            is_product=False,
            annotation_status=AnnotationStatus.ACCEPTED,
        ),
    ]
    predictions = [
        {
            "item_code": "7290117906422",
            "pred_is_product": True,
            "pred_category": "Frozen",
            "pred_brand": None,
            "pred_normalized_name_en": "aguz kshu claiy ank 150 gr",
            "pred_quantity": 150.0,
            "pred_unit": "gr",
        },
        {
            "item_code": "np-026",
            "pred_is_product": False,
            "pred_category": None,
            "pred_brand": None,
            "pred_normalized_name_en": None,
            "pred_quantity": None,
            "pred_unit": None,
        },
    ]
    metrics = evaluate(gold, predictions)
    assert metrics["n_joined"] == 2
    assert metrics["layer1"]["quantity_accuracy"] == 1.0
    assert metrics["layer1"]["unit_accuracy"] == 1.0  # gr → g
    assert metrics["layer1"]["category_accuracy_silver"] == 0.0
    assert metrics["layer2"]["attribute_accuracy"]["quantity"]["accuracy"] == 1.0
    assert metrics["layer2"]["attribute_accuracy"]["product_type"]["n"] == 0.0


def test_evaluate_critical_miss_empty_name() -> None:
    gold = [
        AnnotationRow(
            item_code="1",
            raw_item_name="קשיו",
            is_product=True,
            category="Snacks & Sweets",
            gold_name_en="Cashews",
            gold_quantity=None,
            gold_unit=None,
            annotation_status=AnnotationStatus.CORRECTED,
        )
    ]
    predictions = [
        {
            "item_code": "1",
            "pred_is_product": True,
            "pred_category": "Snacks & Sweets",
            "pred_brand": None,
            "pred_normalized_name_en": None,
            "pred_quantity": None,
            "pred_unit": None,
        }
    ]
    metrics = evaluate(gold, predictions)
    assert metrics["layer2"]["critical_miss_count"] == 1


def test_write_translation_errors(tmp_path: Path) -> None:
    gold = [
        AnnotationRow(
            item_code="1",
            raw_item_name="חלב 1ל",
            is_product=True,
            gold_name_en="Milk 1 L",
            gold_quantity=1,
            gold_unit="L",
            annotation_status=AnnotationStatus.ACCEPTED,
        )
    ]
    predictions = [
        {
            "item_code": "1",
            "pred_normalized_name_en": "Chal",
            "pred_brand": None,
            "pred_quantity": 2,
            "pred_unit": "L",
        }
    ]
    path = tmp_path / "err.csv"
    n = write_translation_errors(gold, predictions, path)
    assert n == 1
    text = path.read_text(encoding="utf-8")
    assert "quantity" in text
