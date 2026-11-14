"""Unit registry, derived totals and sample-file parsing."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.measurement_extraction.loader import load_sample_file
from src.measurement_extraction.schema import (
    Annotation,
    Describes,
    Measurement,
    Role,
    Scope,
)
from src.measurement_extraction.units import (
    apply_canonical,
    canonicalize,
    derived_total,
)


@pytest.mark.parametrize(
    ("amount", "unit", "expected", "canonical"),
    [
        ("1", 'ק"ג', "1000", "g"),
        ("1.5", "קג", "1500", "g"),
        ("900", "ג", "900", "g"),
        ("500", "גרם", "500", "g"),
        ("250", 'מ"ל', "250", "mL"),
        ("1.98", "ליטר", "1980.00", "mL"),
        ("33", 'ס"ל', "330", "mL"),
        ("500", "mg", "0.500", "g"),
    ],
)
def test_known_units_convert(amount, unit, expected, canonical) -> None:
    value, canon, _ = canonicalize(Decimal(amount), unit)
    assert value == Decimal(expected) and canon == canonical


@pytest.mark.parametrize("unit", ["מ", "oz", None, ""])
def test_ambiguous_units_stay_unresolved(unit) -> None:
    assert canonicalize(Decimal(160), unit) == (None, None, None)


def test_known_unit_without_amount_keeps_family() -> None:
    assert canonicalize(None, "מל") == (None, "mL", Describes.VOLUME)


def test_apply_canonical_fills_fields() -> None:
    entry = apply_canonical(Measurement(source_amount=Decimal(1), source_unit='ק"ג'))
    assert (entry.amount, entry.unit, entry.describes) == (
        Decimal(1000),
        "g",
        Describes.MASS,
    )


def _entry(**kw) -> Measurement:
    return Measurement(amount=Decimal(330), unit="mL", **kw)


def test_per_item_total_multiplies() -> None:
    entry = _entry(
        measurement_role=Role.CONTENTS, amount_scope=Scope.PER_ITEM, package_count=6
    )
    assert derived_total(entry) == Decimal(1980)


def test_whole_package_total_not_multiplied() -> None:
    entry = Measurement(
        amount=Decimal(1980),
        unit="mL",
        measurement_role=Role.CONTENTS,
        amount_scope=Scope.WHOLE_PACKAGE,
        package_count=6,
    )
    assert derived_total(entry) == Decimal(1980)


def test_capacity_and_unknown_scope_have_no_total() -> None:
    assert (
        derived_total(
            _entry(
                measurement_role=Role.CAPACITY,
                amount_scope=Scope.PER_ITEM,
                package_count=6,
            )
        )
        is None
    )
    assert (
        derived_total(_entry(measurement_role=Role.CONTENTS, package_count=4)) is None
    )


def test_boolean_must_match_list() -> None:
    with pytest.raises(ValueError):
        Annotation(has_measurement=True, measurements=[])
    with pytest.raises(ValueError):
        Measurement(describes=Describes.OTHER)


def test_loader_keeps_ids_and_quotes(tmp_path) -> None:
    path = tmp_path / "s.txt"
    path.write_text('0012,"עוגיות תפו""א 500 גרם"\n7290,גזר ארוז\n', encoding="utf-8")
    sample = load_sample_file(path)
    assert [p.item_code for p in sample.products] == ["0012", "7290"]
    assert sample.products[0].item_name == 'עוגיות תפו"א 500 גרם'
    assert not sample.had_header
