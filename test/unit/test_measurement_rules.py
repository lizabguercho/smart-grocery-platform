"""Rule baseline, Qwen output parsing and cascade routing."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.measurement_extraction.cascade import route
from src.measurement_extraction.qwen import parse_output
from src.measurement_extraction.rules import extract


def _first(title: str):
    return extract(title).annotation.measurements[0]


def test_attached_and_quoted_units() -> None:
    entry = _first('דלוקס ספריי לעיצוב250מ"ל')
    assert (entry.amount, entry.unit, entry.source_unit) == (Decimal(250), "mL", 'מ"ל')
    assert _first("עוגיות קרם סנדוויץ-900 ג").amount == Decimal(900)
    assert _first('תינוקלין 1.25 ק"ג חד').amount == Decimal(1250)


def test_no_measurement_and_out_of_scope_numbers() -> None:
    assert not extract("גזר ארוז").annotation.has_measurement
    assert not extract("גב.קשה35% בשר").annotation.has_measurement
    assert not extract("שמיכת קיץ יחיד 150*2").annotation.has_measurement
    assert not extract("שרדונה 2022").annotation.has_measurement
    assert not extract("תוחם שפתיים 08").annotation.has_measurement


def test_ambiguous_fragment_and_trailing_number_stay_unresolved() -> None:
    assert not extract("בקבוק האכלה לתינוק 160 מ").annotation.measurements[0].unit
    trailing = _first("ספרי מקבע איפור 200")
    assert trailing.source_amount == Decimal(200) and trailing.unit is None


def test_count_and_scope_not_invented() -> None:
    entry = _first("רביעייה טונה גאיה 140 גר")
    assert (
        entry.package_count == 4
        and entry.amount == Decimal(140)
        and entry.amount_scope is None
    )
    assert _first("ערכת 5 מברשות לעיניים").package_count == 5


def test_capacity_word_changes_role() -> None:
    assert _first("דלי פטנט מתקפל 10 ליטר").measurement_role.value == "capacity"


def test_cascade_routes_only_clean_cases() -> None:
    assert route(extract('קינמון טחון 1 ק"ג')) == "rules"
    assert route(extract("ספרי מקבע איפור 200")) == "qwen"
    assert route(extract("קפה 200 גרם 3 יח")) == "qwen"
    assert route(extract("גזר ארוז")) == "qwen"


@pytest.mark.parametrize(
    "raw", ["not json", '{"has_measurement": true, "measurements": []}']
)
def test_bad_model_output_is_failure_not_negative(raw) -> None:
    annotation, status, _ = parse_output(raw, "x")
    assert annotation is None and status != "ok"


def test_model_output_parsed_and_grounding_flagged() -> None:
    raw = '{"has_measurement": true, "measurements": [{"source_text": "200 גרם", "source_amount": 200, "source_unit": "גרם"}]}'
    annotation, status, ungrounded = parse_output(raw, "קפה 200 גרם")
    assert status == "ok" and annotation.measurements[0].unit == "g" and not ungrounded
    assert parse_output(raw, "קפה")[2] == ["200 גרם"]
