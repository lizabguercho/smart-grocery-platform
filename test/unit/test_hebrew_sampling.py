"""Seeded, exclusion-aware Hebrew product sampling (no live database)."""

from __future__ import annotations

from typing import Self

import pytest

from src.product_translation.exclusions import exclusion_like_patterns
from src.product_translation.sampling import (
    SAMPLE_HEBREW_PRODUCTS_SQL,
    sample_hebrew_products,
)


class FakeCursor:
    def __init__(self, rows=None) -> None:
        self.rows = rows or []
        self.statements: list[tuple[str, object]] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> None:
        return None

    def execute(self, sql, params=None) -> None:
        self.statements.append((sql, params))

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> FakeCursor:
        return self._cursor


def test_unseeded_sample_runs_one_query_without_exclusions() -> None:
    cursor = FakeCursor(rows=[(14, "נילוס 200 גר")])
    products = sample_hebrew_products(FakeConnection(cursor), 5)
    assert cursor.statements == [(SAMPLE_HEBREW_PRODUCTS_SQL, (exclusion_like_patterns(), [], 5))]
    assert products[0].item_name == "נילוס 200 גר"


def test_seed_is_set_first_and_excluded_codes_are_passed() -> None:
    cursor = FakeCursor()
    sample_hebrew_products(FakeConnection(cursor), 3, seed=0.5, exclude_codes=["7290001", "42"])
    assert cursor.statements[0] == ("SELECT setseed(%s)", (0.5,))
    assert cursor.statements[1][1] == (exclusion_like_patterns(), ["7290001", "42"], 3)
    assert "item_code <> ALL(%s)" in SAMPLE_HEBREW_PRODUCTS_SQL


def test_limit_must_be_positive() -> None:
    with pytest.raises(ValueError):
        sample_hebrew_products(FakeConnection(FakeCursor()), 0)
