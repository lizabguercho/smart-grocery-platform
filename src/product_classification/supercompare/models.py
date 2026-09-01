from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.product_classification.models import SuperCompareProduct


@dataclass(frozen=True)
class CategoryNode:
    slug: str
    subcategory_slugs: tuple[str, ...]


@dataclass(frozen=True)
class CategoryPage:
    category_slug: str
    subcategory_slug: str
    page_number: int
    total_pages: int
    products: tuple[SuperCompareProduct, ...]


@dataclass(frozen=True)
class CrawlFailure:
    category_slug: str
    subcategory_slug: str
    page_number: int | None
    error: str


@dataclass(frozen=True)
class CrawlSummary:
    categories: int
    subcategories: int
    expected_pages: int
    downloaded_pages: int
    cached_pages: int
    products: int
    failures: tuple[CrawlFailure, ...]
    products_path: Path | None

    @property
    def succeeded(self) -> bool:
        return not self.failures
