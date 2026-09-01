from __future__ import annotations

import logging
import os
import random
import ssl
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Self

import requests
from bs4 import BeautifulSoup

from src.product_classification.models import SuperCompareProduct
from src.product_classification.supercompare.config import (
    RETRYABLE_STATUS_CODES,
    SuperCompareConfig,
)
from src.product_classification.supercompare.models import CategoryNode, CategoryPage

LOGGER = logging.getLogger(__name__)


def slug_to_name(slug: str) -> str:
    name = slug.replace("-", " ")
    return name.replace(" and ", " & ").title()


class SuperCompareClient:
    def __init__(
        self,
        config: SuperCompareConfig,
        *,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        random_value: Callable[[], float] = random.random,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self._owns_session = session is None
        self._sleep = sleep
        self._monotonic = monotonic
        self._random_value = random_value
        self._now = now
        self._last_request_started_at: float | None = None
        self.session.headers.update({"User-Agent": config.user_agent})

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def validate_ca_bundle(self) -> Path:
        configured_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get(
            "CURL_CA_BUNDLE"
        )
        bundle_path = Path(configured_bundle or requests.certs.where())

        if not bundle_path.exists():
            raise ValueError(f"CA bundle does not exist: {bundle_path}")

        try:
            if bundle_path.is_dir():
                ssl.create_default_context(capath=str(bundle_path))
            else:
                if bundle_path.stat().st_size == 0:
                    raise ValueError(f"CA bundle is empty: {bundle_path}")
                ssl.create_default_context(cafile=str(bundle_path))
        except (OSError, ssl.SSLError) as error:
            raise ValueError(f"CA bundle is not usable: {bundle_path}") from error

        LOGGER.info("Validated CA bundle at %s", bundle_path)
        return bundle_path

    def discover_taxonomy(self) -> tuple[CategoryNode, ...]:
        category_html = self._get_text(f"{self.config.base_url}/he/categories")
        category_slugs = self._parse_category_slugs(category_html)
        nodes: list[CategoryNode] = []

        for category_slug in category_slugs:
            category_url = f"{self.config.base_url}/he/categories/{category_slug}"
            subcategory_html = self._get_text(category_url)
            subcategory_slugs = self._parse_subcategory_slugs(
                subcategory_html,
                category_slug,
            )
            nodes.append(
                CategoryNode(
                    slug=category_slug,
                    subcategory_slugs=subcategory_slugs,
                )
            )
            LOGGER.info(
                "Discovered category %s with %d subcategories",
                category_slug,
                len(subcategory_slugs),
            )

        if not nodes:
            raise ValueError("SuperCompare taxonomy did not contain any categories")
        return tuple(nodes)

    def fetch_category_page(
        self,
        *,
        category_slug: str,
        subcategory_slug: str,
        page_number: int,
    ) -> CategoryPage:
        url = (
            f"{self.config.base_url}/api/groceries/categories/"
            f"by-slug/{subcategory_slug}/products"
        )
        payload = self._get_json(
            url,
            params={
                "page": page_number,
                "limit": self.config.page_size,
                "city": self.config.city,
            },
        )
        return self._parse_category_page(
            payload,
            category_slug=category_slug,
            subcategory_slug=subcategory_slug,
            page_number=page_number,
        )

    def _get_text(self, url: str) -> str:
        response = self._request(url)
        return response.text

    def _get_json(
        self,
        url: str,
        *,
        params: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = self._request(url, params=params)
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise TypeError(f"Expected JSON object from {url}")
        return payload

    def _request(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> requests.Response:
        for attempt in range(1, self.config.max_attempts + 1):
            self._wait_for_request_slot()
            LOGGER.info(
                "Requesting %s params=%s attempt=%d/%d",
                url,
                dict(params or {}),
                attempt,
                self.config.max_attempts,
            )

            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=(
                        self.config.connect_timeout_seconds,
                        self.config.read_timeout_seconds,
                    ),
                )
            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.SSLError,
            ) as error:
                if attempt == self.config.max_attempts:
                    LOGGER.error(
                        "Request failed after %d attempts: %s",
                        attempt,
                        error,
                    )
                    raise
                self._wait_before_retry(
                    attempt=attempt,
                    reason=type(error).__name__,
                )
                continue

            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt == self.config.max_attempts:
                    LOGGER.error(
                        "Request returned HTTP %d after %d attempts",
                        response.status_code,
                        attempt,
                    )
                    response.raise_for_status()
                self._wait_before_retry(
                    attempt=attempt,
                    reason=f"HTTP {response.status_code}",
                    retry_after=response.headers.get("Retry-After"),
                )
                continue

            response.raise_for_status()
            LOGGER.debug("Request completed with HTTP %d", response.status_code)
            return response

        raise RuntimeError("HTTP retry loop ended unexpectedly")

    def _wait_for_request_slot(self) -> None:
        if self._last_request_started_at is not None:
            elapsed = self._monotonic() - self._last_request_started_at
            delay = max(0.0, self.config.request_interval_seconds - elapsed)
            if delay:
                LOGGER.debug("Rate limit delay %.2fs", delay)
                self._sleep(delay)
        self._last_request_started_at = self._monotonic()

    def _wait_before_retry(
        self,
        *,
        attempt: int,
        reason: str,
        retry_after: str | None = None,
    ) -> None:
        delay = self._retry_after_seconds(retry_after)
        if delay is None:
            ceiling = min(
                self.config.backoff_max_seconds,
                self.config.backoff_initial_seconds * (2 ** (attempt - 1)),
            )
            delay = ceiling * self._random_value()

        LOGGER.warning(
            "Transient request failure (%s); retrying after %.2fs (next attempt %d/%d)",
            reason,
            delay,
            attempt + 1,
            self.config.max_attempts,
        )
        self._sleep(delay)

    def _retry_after_seconds(self, value: str | None) -> float | None:
        if not value:
            return None
        try:
            delay = float(value)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                delay = (retry_at - self._now()).total_seconds()
            except (TypeError, ValueError, OverflowError):
                LOGGER.warning("Ignoring invalid Retry-After header: %r", value)
                return None
        return min(
            max(0.0, delay),
            self.config.retry_after_max_seconds,
        )

    @staticmethod
    def _parse_category_slugs(html: str) -> tuple[str, ...]:
        soup = BeautifulSoup(html, "html.parser")
        slugs: set[str] = set()

        for link in soup.find_all("a", href=True):
            href = link.get("href")
            if isinstance(href, str) and "/he/categories/" in href:
                slugs.add(href.rstrip("/").split("/")[-1])

        return tuple(sorted(slugs))

    @staticmethod
    def _parse_subcategory_slugs(
        html: str,
        category_slug: str,
    ) -> tuple[str, ...]:
        soup = BeautifulSoup(html, "html.parser")
        slugs: set[str] = set()

        for link in soup.find_all("a", href=True):
            href = link.get("href")
            classes = link.get("class") or []
            if not isinstance(href, str) or "/he/categories/" not in href:
                continue
            slug = href.rstrip("/").split("/")[-1]
            if slug != category_slug and "rounded-full" in classes:
                slugs.add(slug)

        return tuple(sorted(slugs))

    def _parse_category_page(
        self,
        payload: Mapping[str, Any],
        *,
        category_slug: str,
        subcategory_slug: str,
        page_number: int,
    ) -> CategoryPage:
        total_pages = payload.get("totalPages")
        raw_products = payload.get("data")

        if (
            not isinstance(total_pages, int)
            or isinstance(total_pages, bool)
            or total_pages < 1
        ):
            raise ValueError(
                f"Invalid totalPages for {subcategory_slug} page {page_number}"
            )
        if not isinstance(raw_products, list):
            raise TypeError(
                f"Invalid data list for {subcategory_slug} page {page_number}"
            )

        products = tuple(
            self._parse_product(
                raw_product,
                category_slug=category_slug,
                subcategory_slug=subcategory_slug,
            )
            for raw_product in raw_products
        )
        return CategoryPage(
            category_slug=category_slug,
            subcategory_slug=subcategory_slug,
            page_number=page_number,
            total_pages=total_pages,
            products=products,
        )

    def _parse_product(
        self,
        payload: object,
        *,
        category_slug: str,
        subcategory_slug: str,
    ) -> SuperCompareProduct:
        if not isinstance(payload, Mapping):
            raise TypeError(f"Invalid product in {subcategory_slug}")

        item_code = payload.get("itemCode")
        item_name = payload.get("itemName")
        manufacturer = payload.get("manufacturerName")

        if not isinstance(item_code, (str, int)) or isinstance(item_code, bool):
            raise TypeError(f"Invalid itemCode in {subcategory_slug}")
        if not isinstance(item_name, str):
            raise TypeError(f"Invalid itemName in {subcategory_slug}")
        if not item_name.strip():
            raise ValueError(f"Invalid itemName in {subcategory_slug}")
        if manufacturer is not None and not isinstance(manufacturer, str):
            raise TypeError(f"Invalid manufacturerName in {subcategory_slug}")

        return SuperCompareProduct(
            item_code=str(item_code),
            product_name=item_name,
            manufacturer=manufacturer,
            main_category=slug_to_name(category_slug),
            subcategory=slug_to_name(subcategory_slug),
            source_url=f"{self.config.base_url}/he/product/{item_code}",
        )
