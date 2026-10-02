"""Run a small translation batch: fetch → translate → save.

One failed name does not stop the rest of the batch. Each successful
translation is committed immediately so a crash does not lose work.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from src.product_translation.config import (
    RETRY_FAILED_BATCH_SIZE,
    SAMPLE_BATCH_SIZE,
    TEST_BATCH_SIZE,
)
from src.product_translation.quality import failure_reasons, is_failed_translation
from src.product_translation.repository import ProductToTranslate, TranslatedProduct


class TranslatesProductNames(Protocol):
    def translate(self, hebrew_name: str) -> str: ...


class StoresProductTranslations(Protocol):
    def ensure_english_name_column(self) -> None: ...

    def fetch_products_missing_english_name(
        self, limit: int = TEST_BATCH_SIZE
    ) -> list[ProductToTranslate]: ...

    def fetch_hebrew_product_names(
        self, limit: int = SAMPLE_BATCH_SIZE
    ) -> list[ProductToTranslate]: ...

    def save_english_name(self, item_code: int, english_name: str) -> None: ...

    def fetch_translated_products(self) -> list[TranslatedProduct]: ...

    def overwrite_english_name(self, item_code: int, english_name: str) -> None: ...


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranslationSummary:
    attempted: int
    saved: int
    skipped_failures: int


@dataclass(frozen=True)
class RetryRow:
    item_code: int
    item_name: str
    item_name_en_before: str
    item_name_en_after: str
    reasons_before: str
    reasons_after: str


class ProductNameTranslationJob:
    def __init__(
        self,
        repository: StoresProductTranslations,
        translator: TranslatesProductNames,
    ) -> None:
        self._repository = repository
        self._translator = translator

    def run(self, limit: int = TEST_BATCH_SIZE) -> TranslationSummary:
        self._repository.ensure_english_name_column()
        products = self._repository.fetch_products_missing_english_name(limit)
        logger.info("Found %s product(s) without item_name_en (limit=%s)", len(products), limit)

        saved = 0
        skipped_failures = 0
        for index, product in enumerate(products, start=1):
            try:
                english_name = self._translator.translate(product.item_name)
                self._repository.save_english_name(product.item_code, english_name)
            except Exception:
                skipped_failures += 1
                logger.exception(
                    "[%s/%s] Failed item_code=%s name=%r",
                    index,
                    len(products),
                    product.item_code,
                    product.item_name,
                )
                continue

            saved += 1
            logger.info(
                "[%s/%s] item_code=%s | %s → %s",
                index,
                len(products),
                product.item_code,
                product.item_name,
                english_name,
            )

        summary = TranslationSummary(
            attempted=len(products),
            saved=saved,
            skipped_failures=skipped_failures,
        )
        logger.info(
            "Done. attempted=%s saved=%s failed=%s",
            summary.attempted,
            summary.saved,
            summary.skipped_failures,
        )
        return summary

    def run_hebrew_sample(
        self, limit: int = SAMPLE_BATCH_SIZE
    ) -> tuple[TranslationSummary, list[RetryRow]]:
        """Translate a random sample of Hebrew catalog names.

        Input is always grocery.products.item_name. Existing item_name_en
        for the sampled barcodes is replaced.
        """

        self._repository.ensure_english_name_column()
        products = self._repository.fetch_hebrew_product_names(limit)
        logger.info(
            "Using %s real Hebrew item_name value(s) from grocery.products",
            len(products),
        )

        saved = 0
        skipped_failures = 0
        rows: list[RetryRow] = []
        for index, product in enumerate(products, start=1):
            try:
                english_name = self._translator.translate(product.item_name)
                self._repository.overwrite_english_name(product.item_code, english_name)
            except Exception:
                skipped_failures += 1
                logger.exception(
                    "[%s/%s] Failed item_code=%s name=%r",
                    index,
                    len(products),
                    product.item_code,
                    product.item_name,
                )
                continue

            saved += 1
            rows.append(
                RetryRow(
                    item_code=product.item_code,
                    item_name=product.item_name,
                    item_name_en_before="",
                    item_name_en_after=english_name,
                    reasons_before="",
                    reasons_after="",
                )
            )
            logger.info(
                "[%s/%s] item_code=%s | %s → %s",
                index,
                len(products),
                product.item_code,
                product.item_name,
                english_name,
            )

        summary = TranslationSummary(
            attempted=len(products),
            saved=saved,
            skipped_failures=skipped_failures,
        )
        logger.info(
            "Sample done. attempted=%s saved=%s failed=%s",
            summary.attempted,
            summary.saved,
            summary.skipped_failures,
        )
        return summary, rows

    def retry_failed(
        self, limit: int = RETRY_FAILED_BATCH_SIZE
    ) -> tuple[TranslationSummary, list[RetryRow]]:
        """Re-translate up to `limit` rows that fail the automatic quality flags."""

        self._repository.ensure_english_name_column()
        translated = self._repository.fetch_translated_products()
        failed = [
            row
            for row in translated
            if is_failed_translation(row.item_name, row.item_name_en)
        ][:limit]
        logger.info(
            "Flagged %s failed translation(s); retrying %s",
            sum(
                1
                for row in translated
                if is_failed_translation(row.item_name, row.item_name_en)
            ),
            len(failed),
        )

        saved = 0
        skipped_failures = 0
        retries: list[RetryRow] = []
        for index, product in enumerate(failed, start=1):
            before = product.item_name_en
            reasons_before = ";".join(
                failure_reasons(product.item_name, before)
            )
            try:
                english_name = self._translator.translate(product.item_name)
                self._repository.overwrite_english_name(
                    product.item_code, english_name
                )
            except Exception:
                skipped_failures += 1
                logger.exception(
                    "[%s/%s] Retry failed item_code=%s name=%r",
                    index,
                    len(failed),
                    product.item_code,
                    product.item_name,
                )
                continue

            saved += 1
            reasons_after = ";".join(
                failure_reasons(product.item_name, english_name)
            )
            retries.append(
                RetryRow(
                    item_code=product.item_code,
                    item_name=product.item_name,
                    item_name_en_before=before,
                    item_name_en_after=english_name,
                    reasons_before=reasons_before,
                    reasons_after=reasons_after,
                )
            )
            logger.info(
                "[%s/%s] item_code=%s | %s | before=%r after=%r | flags %s → %s",
                index,
                len(failed),
                product.item_code,
                product.item_name,
                before,
                english_name,
                reasons_before or "none",
                reasons_after or "none",
            )

        summary = TranslationSummary(
            attempted=len(failed),
            saved=saved,
            skipped_failures=skipped_failures,
        )
        logger.info(
            "Retry done. attempted=%s saved=%s failed=%s",
            summary.attempted,
            summary.saved,
            summary.skipped_failures,
        )
        return summary, retries
