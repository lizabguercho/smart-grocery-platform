"""Manifest grouping, shortfall reporting and leakage checks."""

from __future__ import annotations

import pytest

from src.measurement_extraction.loader import SampleFile, SampleProduct
from src.measurement_extraction.manifests import (
    assert_no_leakage,
    build_dev_manifest,
)


def _sample(*pairs: tuple[str, str]) -> SampleFile:
    return SampleFile([SampleProduct(*p) for p in pairs], "hash", False)


def test_duplicates_removed_and_shortfall_reported() -> None:
    manifest = build_dev_manifest(
        _sample(
            ("1", "קפה 200ג"), ("1", "קפה 200ג"), ("2", "קפה 200 ג"), ("3", "קפה 500ג")
        ),
        size=5,
    )
    assert [e.item_code for e in manifest.entries] == ["1", "3"]
    assert len(manifest.exclusions) == 2 and manifest.shortfall == 3


def test_selection_is_deterministic_when_oversized() -> None:
    sample = _sample(*[(str(i), f"מוצר {i}") for i in range(30)])
    a = build_dev_manifest(sample, size=10, seed=1)
    b = build_dev_manifest(sample, size=10, seed=1)
    assert a.entries == b.entries and len(a.entries) == 10


def test_leakage_detected() -> None:
    dev = build_dev_manifest(_sample(("1", "א"), ("2", "ב")), size=2)
    test = build_dev_manifest(_sample(("3", "ב"), ("4", "ג")), size=2)
    with pytest.raises(ValueError):
        assert_no_leakage(dev, test)
