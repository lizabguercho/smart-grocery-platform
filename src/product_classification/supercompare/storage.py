from __future__ import annotations

import csv
import json
import logging
import os
import re
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.product_classification.models import SuperCompareProduct
from src.product_classification.supercompare.config import (
    CHECKPOINT_VERSION,
    SuperCompareConfig,
)
from src.product_classification.supercompare.models import (
    CategoryNode,
    CategoryPage,
    CrawlSummary,
)

LOGGER = logging.getLogger(__name__)
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PRODUCT_FIELD_NAMES = tuple(SuperCompareProduct.__dataclass_fields__)


class SuperCompareBatchStore:
    def __init__(self, config: SuperCompareConfig) -> None:
        self.config = config

    @property
    def taxonomy_path(self) -> Path:
        return self.config.raw_dir / "taxonomy.json"

    def page_path(
        self,
        category_slug: str,
        subcategory_slug: str,
        page_number: int,
    ) -> Path:
        self._validate_slug(category_slug)
        self._validate_slug(subcategory_slug)
        if page_number < 1:
            raise ValueError("page_number must be at least 1")
        return (
            self.config.raw_dir
            / category_slug
            / subcategory_slug
            / f"page_{page_number:04d}.json"
        )

    def save_taxonomy(self, taxonomy: tuple[CategoryNode, ...]) -> Path:
        payload = {
            "version": CHECKPOINT_VERSION,
            "categories": [asdict(node) for node in taxonomy],
        }
        self._atomic_write_json(self.taxonomy_path, payload)
        LOGGER.info("Saved taxonomy checkpoint to %s", self.taxonomy_path)
        return self.taxonomy_path

    def load_taxonomy(self) -> tuple[CategoryNode, ...]:
        payload = self._read_json(self.taxonomy_path)
        self._validate_version(payload, self.taxonomy_path)
        categories = payload.get("categories")
        if not isinstance(categories, list):
            raise TypeError(f"Invalid taxonomy checkpoint: {self.taxonomy_path}")

        nodes: list[CategoryNode] = []
        for category in categories:
            if not isinstance(category, dict):
                raise TypeError(f"Invalid taxonomy category in {self.taxonomy_path}")
            slug = category.get("slug")
            subcategory_slugs = category.get("subcategory_slugs")
            if not isinstance(slug, str) or not isinstance(
                subcategory_slugs,
                (list, tuple),
            ):
                raise TypeError(f"Invalid taxonomy category in {self.taxonomy_path}")
            self._validate_slug(slug)
            normalized_subcategories: list[str] = []
            for subcategory_slug in subcategory_slugs:
                if not isinstance(subcategory_slug, str):
                    raise TypeError(
                        f"Invalid taxonomy subcategory in {self.taxonomy_path}"
                    )
                self._validate_slug(subcategory_slug)
                normalized_subcategories.append(subcategory_slug)
            nodes.append(
                CategoryNode(
                    slug=slug,
                    subcategory_slugs=tuple(normalized_subcategories),
                )
            )

        if not nodes:
            raise ValueError(f"Taxonomy checkpoint is empty: {self.taxonomy_path}")
        LOGGER.info("Loaded taxonomy checkpoint from %s", self.taxonomy_path)
        return tuple(nodes)

    def save_page(self, page: CategoryPage) -> Path:
        path = self.page_path(
            page.category_slug,
            page.subcategory_slug,
            page.page_number,
        )
        payload = {
            "version": CHECKPOINT_VERSION,
            "category_slug": page.category_slug,
            "subcategory_slug": page.subcategory_slug,
            "page_number": page.page_number,
            "total_pages": page.total_pages,
            "products": [asdict(product) for product in page.products],
        }
        self._atomic_write_json(path, payload)
        LOGGER.info(
            "Saved page checkpoint %s/%s page %d with %d products",
            page.category_slug,
            page.subcategory_slug,
            page.page_number,
            len(page.products),
        )
        return path

    def load_page(
        self,
        category_slug: str,
        subcategory_slug: str,
        page_number: int,
    ) -> CategoryPage | None:
        path = self.page_path(category_slug, subcategory_slug, page_number)
        if not path.exists():
            return None

        payload = self._read_json(path)
        self._validate_version(payload, path)
        if (
            payload.get("category_slug") != category_slug
            or payload.get("subcategory_slug") != subcategory_slug
            or payload.get("page_number") != page_number
        ):
            raise ValueError(f"Checkpoint identity mismatch: {path}")

        total_pages = payload.get("total_pages")
        products_payload = payload.get("products")
        if (
            not isinstance(total_pages, int)
            or isinstance(total_pages, bool)
            or total_pages < page_number
            or not isinstance(products_payload, list)
        ):
            raise ValueError(f"Invalid page checkpoint: {path}")

        products = tuple(
            self._product_from_dict(product_payload, path)
            for product_payload in products_payload
        )
        return CategoryPage(
            category_slug=category_slug,
            subcategory_slug=subcategory_slug,
            page_number=page_number,
            total_pages=total_pages,
            products=products,
        )

    def export_products(self, pages: list[CategoryPage]) -> Path:
        output_path = self.config.products_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                newline="",
                encoding="utf-8",
                dir=output_path.parent,
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                writer = csv.DictWriter(
                    temporary_file,
                    fieldnames=PRODUCT_FIELD_NAMES,
                )
                writer.writeheader()
                for page in pages:
                    for product in page.products:
                        writer.writerow(asdict(product))
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, output_path)
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

        LOGGER.info("Atomically exported products to %s", output_path)
        return output_path

    def load_products(self) -> list[SuperCompareProduct]:
        products: list[SuperCompareProduct] = []
        with self.config.products_path.open(
            newline="",
            encoding="utf-8",
        ) as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != PRODUCT_FIELD_NAMES:
                raise ValueError(
                    f"Invalid SuperCompare CSV header: {self.config.products_path}"
                )
            for row in reader:
                products.append(
                    SuperCompareProduct(
                        item_code=row["item_code"],
                        product_name=row["product_name"],
                        manufacturer=row["manufacturer"] or None,
                        main_category=row["main_category"],
                        subcategory=row["subcategory"],
                        source_url=row["source_url"],
                    )
                )
        return products

    def save_report(self, summary: CrawlSummary) -> Path:
        payload = {
            "version": CHECKPOINT_VERSION,
            "succeeded": summary.succeeded,
            "categories": summary.categories,
            "subcategories": summary.subcategories,
            "expected_pages": summary.expected_pages,
            "downloaded_pages": summary.downloaded_pages,
            "cached_pages": summary.cached_pages,
            "products": summary.products,
            "products_path": (
                str(summary.products_path)
                if summary.products_path is not None
                else None
            ),
            "failures": [asdict(failure) for failure in summary.failures],
        }
        self._atomic_write_json(self.config.report_path, payload)
        LOGGER.info("Saved crawl report to %s", self.config.report_path)
        return self.config.report_path

    @staticmethod
    def _validate_slug(slug: str) -> None:
        if not SLUG_PATTERN.fullmatch(slug):
            raise ValueError(f"Invalid SuperCompare slug: {slug!r}")

    @staticmethod
    def _product_from_dict(
        payload: object,
        checkpoint_path: Path,
    ) -> SuperCompareProduct:
        if not isinstance(payload, dict):
            raise TypeError(f"Invalid product in checkpoint: {checkpoint_path}")
        if set(payload) != set(PRODUCT_FIELD_NAMES):
            raise ValueError(f"Invalid product fields in checkpoint: {checkpoint_path}")

        required_string_fields = (
            "item_code",
            "product_name",
            "main_category",
            "subcategory",
            "source_url",
        )
        if any(not isinstance(payload[field], str) for field in required_string_fields):
            raise ValueError(f"Invalid product values in checkpoint: {checkpoint_path}")
        manufacturer = payload["manufacturer"]
        if manufacturer is not None and not isinstance(manufacturer, str):
            raise ValueError(f"Invalid manufacturer in checkpoint: {checkpoint_path}")

        return SuperCompareProduct(**payload)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            with path.open(encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Cannot read checkpoint: {path}") from error
        if not isinstance(payload, dict):
            raise TypeError(f"Checkpoint must contain a JSON object: {path}")
        return payload

    @staticmethod
    def _validate_version(payload: dict[str, Any], path: Path) -> None:
        if payload.get("version") != CHECKPOINT_VERSION:
            raise ValueError(f"Unsupported checkpoint version: {path}")

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(
                    payload,
                    temporary_file,
                    ensure_ascii=False,
                    indent=2,
                )
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, path)
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise
