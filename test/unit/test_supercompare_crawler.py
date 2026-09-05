from __future__ import annotations

from pathlib import Path

import requests

from src.product_classification.models import SuperCompareProduct
from src.product_classification.supercompare.config import SuperCompareConfig
from src.product_classification.supercompare.crawler import SuperCompareCrawler
from src.product_classification.supercompare.models import CategoryNode, CategoryPage
from src.product_classification.supercompare.storage import SuperCompareBatchStore


def make_config(tmp_path: Path, *, resume: bool = True) -> SuperCompareConfig:
    return SuperCompareConfig(
        raw_dir=tmp_path / "raw",
        products_path=tmp_path / "processed" / "products.csv",
        report_path=tmp_path / "processed" / "report.json",
        log_path=tmp_path / "logs" / "crawler.log",
        resume=resume,
    )


def make_page(page_number: int, total_pages: int = 2) -> CategoryPage:
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


class FakeClient:
    def __init__(
        self,
        pages: dict[int, CategoryPage | Exception],
        *,
        taxonomy_error: Exception | None = None,
    ) -> None:
        self.pages = pages
        self.taxonomy_error = taxonomy_error
        self.fetch_calls: list[int] = []
        self.ca_validated = False

    def validate_ca_bundle(self) -> Path:
        self.ca_validated = True
        return Path("ca.pem")

    def discover_taxonomy(self) -> tuple[CategoryNode, ...]:
        if self.taxonomy_error is not None:
            raise self.taxonomy_error
        return (
            CategoryNode(
                slug="dairy-and-eggs",
                subcategory_slugs=("milk",),
            ),
        )

    def fetch_category_page(
        self,
        *,
        category_slug: str,
        subcategory_slug: str,
        page_number: int,
    ) -> CategoryPage:
        assert category_slug == "dairy-and-eggs"
        assert subcategory_slug == "milk"
        self.fetch_calls.append(page_number)
        result = self.pages[page_number]
        if isinstance(result, Exception):
            raise result
        return result


def test_crawler_checkpoints_pages_and_exports_complete_run(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    store = SuperCompareBatchStore(config)
    client = FakeClient({1: make_page(1), 2: make_page(2)})
    crawler = SuperCompareCrawler(
        config,
        client,  # type: ignore[arg-type]
        store,
    )

    summary = crawler.run()

    assert summary.succeeded is True
    assert summary.downloaded_pages == 2
    assert summary.products == 2
    assert client.ca_validated is True
    assert config.products_path.exists()
    assert store.load_page("dairy-and-eggs", "milk", 2) == make_page(2)


def test_crawler_resume_uses_valid_page_checkpoints(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    store = SuperCompareBatchStore(config)
    store.save_page(make_page(1))
    store.save_page(make_page(2))
    client = FakeClient({})
    crawler = SuperCompareCrawler(
        config,
        client,  # type: ignore[arg-type]
        store,
    )

    summary = crawler.run()

    assert summary.succeeded is True
    assert summary.cached_pages == 2
    assert summary.downloaded_pages == 0
    assert client.fetch_calls == []


def test_crawler_failure_preserves_previous_csv_and_reports_failure(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    config.products_path.parent.mkdir(parents=True)
    config.products_path.write_text("previous export\n", encoding="utf-8")
    store = SuperCompareBatchStore(config)
    client = FakeClient(
        {
            1: make_page(1),
            2: requests.exceptions.SSLError("temporary TLS error"),
        }
    )
    crawler = SuperCompareCrawler(
        config,
        client,  # type: ignore[arg-type]
        store,
    )

    summary = crawler.run()

    assert summary.succeeded is False
    assert len(summary.failures) == 1
    assert summary.failures[0].page_number == 2
    assert config.products_path.read_text(encoding="utf-8") == "previous export\n"
    assert config.report_path.exists()


def test_crawler_uses_cached_taxonomy_when_discovery_fails(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    store = SuperCompareBatchStore(config)
    store.save_taxonomy(
        (
            CategoryNode(
                slug="dairy-and-eggs",
                subcategory_slugs=("milk",),
            ),
        )
    )
    client = FakeClient(
        {1: make_page(1, total_pages=1)},
        taxonomy_error=requests.ConnectionError("offline"),
    )
    crawler = SuperCompareCrawler(
        config,
        client,  # type: ignore[arg-type]
        store,
    )

    summary = crawler.run()

    assert summary.succeeded is True
    assert summary.downloaded_pages == 1
