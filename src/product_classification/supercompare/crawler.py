from __future__ import annotations

import logging

import requests

from src.product_classification.supercompare.client import SuperCompareClient
from src.product_classification.supercompare.config import SuperCompareConfig
from src.product_classification.supercompare.models import (
    CategoryNode,
    CategoryPage,
    CrawlFailure,
    CrawlSummary,
)
from src.product_classification.supercompare.storage import SuperCompareBatchStore

LOGGER = logging.getLogger(__name__)


class SuperCompareCrawler:
    def __init__(
        self,
        config: SuperCompareConfig,
        client: SuperCompareClient,
        store: SuperCompareBatchStore,
    ) -> None:
        self.config = config
        self.client = client
        self.store = store

    def run(self) -> CrawlSummary:
        self.client.validate_ca_bundle()
        taxonomy = self._load_taxonomy()
        selected_taxonomy = self._select_taxonomy(taxonomy)

        pages: list[CategoryPage] = []
        failures: list[CrawlFailure] = []
        downloaded_pages = 0
        cached_pages = 0
        expected_pages = 0
        subcategory_count = sum(
            len(node.subcategory_slugs) for node in selected_taxonomy
        )

        LOGGER.info(
            "Starting crawl for %d categories and %d subcategories",
            len(selected_taxonomy),
            subcategory_count,
        )

        for node in selected_taxonomy:
            for subcategory_slug in node.subcategory_slugs:
                try:
                    first_page, was_cached = self._get_page(
                        category_slug=node.slug,
                        subcategory_slug=subcategory_slug,
                        page_number=1,
                    )
                except (requests.RequestException, TypeError, ValueError) as error:
                    failures.append(
                        self._failure(
                            node.slug,
                            subcategory_slug,
                            1,
                            error,
                        )
                    )
                    continue

                pages.append(first_page)
                expected_pages += first_page.total_pages
                if was_cached:
                    cached_pages += 1
                else:
                    downloaded_pages += 1

                for page_number in range(2, first_page.total_pages + 1):
                    try:
                        page, was_cached = self._get_page(
                            category_slug=node.slug,
                            subcategory_slug=subcategory_slug,
                            page_number=page_number,
                            expected_total_pages=first_page.total_pages,
                        )
                    except (
                        requests.RequestException,
                        TypeError,
                        ValueError,
                    ) as error:
                        failures.append(
                            self._failure(
                                node.slug,
                                subcategory_slug,
                                page_number,
                                error,
                            )
                        )
                        continue

                    pages.append(page)
                    if was_cached:
                        cached_pages += 1
                    else:
                        downloaded_pages += 1

        products_path = None
        if failures:
            LOGGER.error(
                "Crawl finished with %d failed pages; preserving the previous CSV",
                len(failures),
            )
        else:
            products_path = self.store.export_products(pages)

        summary = CrawlSummary(
            categories=len(selected_taxonomy),
            subcategories=subcategory_count,
            expected_pages=expected_pages,
            downloaded_pages=downloaded_pages,
            cached_pages=cached_pages,
            products=sum(len(page.products) for page in pages),
            failures=tuple(failures),
            products_path=products_path,
        )
        self.store.save_report(summary)
        LOGGER.info(
            "Crawl summary: products=%d downloaded_pages=%d cached_pages=%d "
            "failures=%d",
            summary.products,
            summary.downloaded_pages,
            summary.cached_pages,
            len(summary.failures),
        )
        return summary

    def _load_taxonomy(self) -> tuple[CategoryNode, ...]:
        try:
            taxonomy = self.client.discover_taxonomy()
        except (requests.RequestException, TypeError, ValueError) as error:
            if not self.config.resume:
                raise
            LOGGER.warning(
                "Live taxonomy discovery failed (%s); loading cached taxonomy",
                error,
            )
            return self.store.load_taxonomy()

        self.store.save_taxonomy(taxonomy)
        return taxonomy

    def _select_taxonomy(
        self,
        taxonomy: tuple[CategoryNode, ...],
    ) -> tuple[CategoryNode, ...]:
        if self.config.category_slug is None:
            return taxonomy

        selected_node = next(
            (node for node in taxonomy if node.slug == self.config.category_slug),
            None,
        )
        if selected_node is None:
            raise ValueError(
                f"Unknown SuperCompare category: {self.config.category_slug}"
            )

        if not self.config.subcategory_slugs:
            return (selected_node,)

        available = set(selected_node.subcategory_slugs)
        missing = set(self.config.subcategory_slugs) - available
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(
                f"Unknown subcategories for {selected_node.slug}: {missing_list}"
            )

        selected_subcategories = tuple(
            subcategory_slug
            for subcategory_slug in selected_node.subcategory_slugs
            if subcategory_slug in self.config.subcategory_slugs
        )
        return (
            CategoryNode(
                slug=selected_node.slug,
                subcategory_slugs=selected_subcategories,
            ),
        )

    def _get_page(
        self,
        *,
        category_slug: str,
        subcategory_slug: str,
        page_number: int,
        expected_total_pages: int | None = None,
    ) -> tuple[CategoryPage, bool]:
        if self.config.resume:
            try:
                cached_page = self.store.load_page(
                    category_slug,
                    subcategory_slug,
                    page_number,
                )
            except (TypeError, ValueError) as error:
                LOGGER.warning(
                    "Ignoring invalid checkpoint for %s/%s page %d: %s",
                    category_slug,
                    subcategory_slug,
                    page_number,
                    error,
                )
            else:
                if cached_page is not None and (
                    expected_total_pages is None
                    or cached_page.total_pages == expected_total_pages
                ):
                    LOGGER.info(
                        "Using cached page %s/%s page %d",
                        category_slug,
                        subcategory_slug,
                        page_number,
                    )
                    return cached_page, True
                if cached_page is not None:
                    LOGGER.warning(
                        "Checkpoint total page count changed for %s/%s page %d; "
                        "downloading it again",
                        category_slug,
                        subcategory_slug,
                        page_number,
                    )

        page = self.client.fetch_category_page(
            category_slug=category_slug,
            subcategory_slug=subcategory_slug,
            page_number=page_number,
        )
        if (
            expected_total_pages is not None
            and page.total_pages != expected_total_pages
        ):
            raise ValueError(
                f"Pagination changed for {subcategory_slug}: expected "
                f"{expected_total_pages}, received {page.total_pages}"
            )
        self.store.save_page(page)
        return page, False

    @staticmethod
    def _failure(
        category_slug: str,
        subcategory_slug: str,
        page_number: int,
        error: Exception,
    ) -> CrawlFailure:
        LOGGER.error(
            "Failed %s/%s page %d: %s",
            category_slug,
            subcategory_slug,
            page_number,
            error,
        )
        return CrawlFailure(
            category_slug=category_slug,
            subcategory_slug=subcategory_slug,
            page_number=page_number,
            error=f"{type(error).__name__}: {error}",
        )
