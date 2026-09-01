from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.product_classification.models import SuperCompareProduct
from src.product_classification.supercompare.config import SuperCompareConfig
from src.product_classification.supercompare.models import (
    CategoryNode,
    CategoryPage,
    CrawlSummary,
)
from src.product_classification.supercompare.storage import SuperCompareBatchStore


def make_config(tmp_path: Path) -> SuperCompareConfig:
    return SuperCompareConfig(
        raw_dir=tmp_path / "raw",
        products_path=tmp_path / "processed" / "products.csv",
        report_path=tmp_path / "processed" / "report.json",
        log_path=tmp_path / "logs" / "crawler.log",
    )


def make_page(page_number: int = 1, total_pages: int = 1) -> CategoryPage:
    return CategoryPage(
        category_slug="dairy-and-eggs",
        subcategory_slug="milk",
        page_number=page_number,
        total_pages=total_pages,
        products=(
            SuperCompareProduct(
                item_code=str(page_number),
                product_name=f"Milk {page_number}",
                manufacturer=None,
                main_category="Dairy & Eggs",
                subcategory="Milk",
                source_url=f"https://example.test/{page_number}",
            ),
        ),
    )


def test_page_checkpoint_round_trip_and_taxonomy_round_trip(
    tmp_path: Path,
) -> None:
    store = SuperCompareBatchStore(make_config(tmp_path))
    taxonomy = (
        CategoryNode(
            slug="dairy-and-eggs",
            subcategory_slugs=("milk", "cheese"),
        ),
    )
    page = make_page()

    store.save_taxonomy(taxonomy)
    store.save_page(page)

    assert store.load_taxonomy() == taxonomy
    assert store.load_page("dairy-and-eggs", "milk", 1) == page


def test_corrupt_page_checkpoint_is_rejected(tmp_path: Path) -> None:
    store = SuperCompareBatchStore(make_config(tmp_path))
    path = store.page_path("dairy-and-eggs", "milk", 1)
    path.parent.mkdir(parents=True)
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(ValueError, match="Cannot read checkpoint"):
        store.load_page("dairy-and-eggs", "milk", 1)


def test_export_rebuilds_csv_from_pages_without_duplicate_headers(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    store = SuperCompareBatchStore(config)

    store.export_products([make_page(1, 2), make_page(2, 2)])

    with config.products_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert [row["item_code"] for row in rows] == ["1", "2"]
    assert len(config.products_path.read_text(encoding="utf-8").splitlines()) == 3


def test_save_report_records_failure_state(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    store = SuperCompareBatchStore(config)
    summary = CrawlSummary(
        categories=1,
        subcategories=1,
        expected_pages=2,
        downloaded_pages=1,
        cached_pages=0,
        products=1,
        failures=(),
        products_path=config.products_path,
    )

    store.save_report(summary)

    report = json.loads(config.report_path.read_text(encoding="utf-8"))
    assert report["succeeded"] is True
    assert report["expected_pages"] == 2
