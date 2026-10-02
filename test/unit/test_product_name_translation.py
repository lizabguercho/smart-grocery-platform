"""Unit tests for Hebrew → English product-name helpers.

These tests never load Qwen and never open PostgreSQL. They check the
rules we control: cleaning model text, skipping Hebrew-free names,
skipping rows that already have item_name_en, and continuing after one
failed translation.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from src.product_translation.exclusions import exclusion_like_patterns
from src.product_translation.config import SYSTEM_PROMPT, TEST_BATCH_SIZE
from src.product_translation.job import ProductNameTranslationJob
from src.product_translation.name_translator import (
    QwenProductNameTranslator,
    clean_translation,
    contains_hebrew,
    skip_slow_packages_distributions,
)
from src.product_translation.quality import failure_reasons, is_failed_translation
from src.product_translation.exclusions import is_excluded_from_translation
from src.product_translation.repository import (
    FETCH_RANDOM_HEBREW_PRODUCTS_SQL,
    FETCH_UNTRANSLATED_SQL,
    OVERWRITE_ENGLISH_NAME_SQL,
    SAVE_ENGLISH_NAME_SQL,
    ProductToTranslate,
    ProductTranslationRepository,
    TranslatedProduct,
)


class FakeCursor:
    def __init__(self, rows: list[tuple[object, object]] | None = None) -> None:
        self.rows = rows or []
        self.statements: list[tuple[str, object]] = []

    def execute(self, sql: str, params: object = None) -> None:
        self.statements.append((sql, params))

    def fetchall(self) -> list[tuple[object, object]]:
        return self.rows

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.commits = 0

    def cursor(self) -> FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.commits += 1


class FakeTranslator:
    def __init__(self, answers: dict[str, str] | None = None, fail_on: str | None = None) -> None:
        self.answers = answers or {}
        self.fail_on = fail_on
        self.calls: list[str] = []

    def translate(self, hebrew_name: str) -> str:
        self.calls.append(hebrew_name)
        if hebrew_name == self.fail_on:
            raise RuntimeError("model exploded")
        return self.answers[hebrew_name]


def test_contains_hebrew_detects_grocery_names() -> None:
    assert contains_hebrew("חלב 3%")
    assert not contains_hebrew("Coca-Cola 1.5L")


def test_clean_translation_keeps_first_line_and_drops_quotes() -> None:
    raw = '"English: Milk 3% 1L"\nThis is a dairy product.'
    assert clean_translation(raw) == "Milk 3% 1L"


def test_clean_translation_empty_input_is_empty() -> None:
    assert clean_translation("   ") == ""
    assert clean_translation("") == ""


def test_translator_skips_model_when_name_has_no_hebrew(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    translator = QwenProductNameTranslator()

    def fail_if_loaded() -> None:
        raise AssertionError("model should not load for English names")

    monkeypatch.setattr(translator, "load", fail_if_loaded)
    assert translator.translate("  Coca-Cola 330ml  ") == "Coca-Cola 330ml"


def test_translator_rejects_blank_names() -> None:
    translator = QwenProductNameTranslator()
    with pytest.raises(ValueError, match="empty"):
        translator.translate("   ")


def test_fetch_query_skips_rows_that_already_have_english_names() -> None:
    assert "item_name_en IS NULL" in FETCH_UNTRANSLATED_SQL
    assert "LIMIT %s" in FETCH_UNTRANSLATED_SQL
    assert "item_name" in FETCH_UNTRANSLATED_SQL


def test_save_query_does_not_overwrite_hebrew_or_existing_english() -> None:
    assert "UPDATE grocery.products" in SAVE_ENGLISH_NAME_SQL
    assert "SET item_name_en" in SAVE_ENGLISH_NAME_SQL
    assert "item_name =" not in SAVE_ENGLISH_NAME_SQL
    assert "item_name_en IS NULL" in SAVE_ENGLISH_NAME_SQL


def test_repository_fetch_maps_rows() -> None:
    cursor = FakeCursor(rows=[(7290001, "חלב 3%"), (7290002, "לחם")])
    repository = ProductTranslationRepository(FakeConnection(cursor))

    products = repository.fetch_products_missing_english_name(limit=2)

    assert products == [
        ProductToTranslate(item_code=7290001, item_name="חלב 3%"),
        ProductToTranslate(item_code=7290002, item_name="לחם"),
    ]
    assert cursor.statements[0][1] == (exclusion_like_patterns(), 2)


def test_repository_save_commits_one_row() -> None:
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = ProductTranslationRepository(connection)

    repository.save_english_name(7290001, "Milk 3%")

    assert cursor.statements == [(SAVE_ENGLISH_NAME_SQL, ("Milk 3%", 7290001))]
    assert connection.commits == 1


def test_job_saves_successes_and_continues_after_a_failure() -> None:
    saved: list[tuple[int, str]] = []
    repository = SimpleNamespace(
        ensure_english_name_column=lambda: None,
        fetch_products_missing_english_name=lambda limit: [
            ProductToTranslate(1, "חלב"),
            ProductToTranslate(2, "לחם"),
            ProductToTranslate(3, "מים"),
        ],
        save_english_name=lambda item_code, english_name: saved.append(
            (item_code, english_name)
        ),
    )
    translator = FakeTranslator(
        answers={"חלב": "Milk", "מים": "Water"},
        fail_on="לחם",
    )

    summary = ProductNameTranslationJob(repository, translator).run(limit=TEST_BATCH_SIZE)

    assert translator.calls == ["חלב", "לחם", "מים"]
    assert saved == [(1, "Milk"), (3, "Water")]
    assert summary.attempted == 3
    assert summary.saved == 2
    assert summary.skipped_failures == 1


def test_skip_slow_packages_distributions_returns_empty_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib.metadata as metadata

    def should_not_run() -> dict[str, list[str]]:
        raise AssertionError("original packages_distributions should not run")

    monkeypatch.setattr(metadata, "packages_distributions", should_not_run)
    skip_slow_packages_distributions()
    assert metadata.packages_distributions() == {}
    skip_slow_packages_distributions()
    assert metadata.packages_distributions() == {}


def test_prompt_asks_for_literal_translation_without_guessing() -> None:
    lowered = SYSTEM_PROMPT.lower()
    assert "literally" in lowered
    assert "never guess or invent" in lowered
    assert "transliterat" in lowered
    assert "output only the translation" in lowered


def test_quality_flags_leftover_hebrew_and_dropped_numbers() -> None:
    reasons = failure_reasons("חלב 3% 1ל", "Fresh Israeli milk")
    assert "hebrew_left_in_english" not in reasons
    assert any(reason.startswith("missing_numbers:") for reason in reasons)
    assert any(reason.startswith("invented_words:") for reason in reasons)
    assert is_failed_translation("חלב 3% 1ל", "חלב 3%")
    assert not is_failed_translation("חלב 3%", "Milk 3%")
    assert not is_failed_translation("אבוקדו ישראל", "Avocado Israel")
    assert is_failed_translation("אבוקדו ישראל", "Ozeki Israel")
    assert is_failed_translation("בטטה ישראל", "Israel Milk")


def test_job_retries_twenty_failed_examples_and_overwrites_english() -> None:
    overwritten: list[tuple[int, str]] = []
    repository = SimpleNamespace(
        ensure_english_name_column=lambda: None,
        fetch_products_missing_english_name=lambda limit: [],
        save_english_name=lambda item_code, english_name: None,
        fetch_translated_products=lambda: [
            TranslatedProduct(1, "חלב 3%", "Fresh Israeli milk"),
            TranslatedProduct(2, "Coca-Cola 1.5L", "Coca-Cola 1.5L"),
            TranslatedProduct(3, "לחם 500", "bread"),
        ],
        overwrite_english_name=lambda item_code, english_name: overwritten.append(
            (item_code, english_name)
        ),
    )
    translator = FakeTranslator(
        answers={"חלב 3%": "Milk 3%", "לחם 500": "Bread 500"},
    )

    summary, retries = ProductNameTranslationJob(repository, translator).retry_failed(
        limit=20
    )

    assert translator.calls == ["חלב 3%", "לחם 500"]
    assert overwritten == [(1, "Milk 3%"), (3, "Bread 500")]
    assert summary.attempted == 2
    assert summary.saved == 2
    assert retries[0].item_name_en_before == "Fresh Israeli milk"
    assert retries[0].item_name_en_after == "Milk 3%"
    assert "invented_words" in retries[0].reasons_before
    assert retries[0].reasons_after == ""
    assert "SET item_name_en" in OVERWRITE_ENGLISH_NAME_SQL
    assert "item_name =" not in OVERWRITE_ENGLISH_NAME_SQL


def test_hebrew_sample_query_is_random_and_skips_service_names() -> None:
    assert "ORDER BY random()" in FETCH_RANDOM_HEBREW_PRODUCTS_SQL
    assert "ILIKE ANY" in FETCH_RANDOM_HEBREW_PRODUCTS_SQL
    assert "item_name_en" not in FETCH_RANDOM_HEBREW_PRODUCTS_SQL
    assert is_excluded_from_translation("משלוח אינטרנט")
    assert is_excluded_from_translation("תו סיבוס פטור מעמ")
    assert is_excluded_from_translation("תן ביס פטור מעמ")
    assert is_excluded_from_translation("איסוף עצמי-אינטרנט")
    assert not is_excluded_from_translation("אבוקדו ישראל")
    assert not is_excluded_from_translation("מגשים למארזי משלוחי מנות")


def test_job_translates_real_hebrew_catalog_names_and_overwrites_english() -> None:
    overwritten: list[tuple[int, str]] = []
    repository = SimpleNamespace(
        ensure_english_name_column=lambda: None,
        fetch_products_missing_english_name=lambda limit: [],
        fetch_hebrew_product_names=lambda limit: [
            ProductToTranslate(14, "נילוס 200 גר"),
            ProductToTranslate(2003, "אבוקדו ישראל"),
        ],
        save_english_name=lambda item_code, english_name: None,
        fetch_translated_products=lambda: [],
        overwrite_english_name=lambda item_code, english_name: overwritten.append(
            (item_code, english_name)
        ),
    )
    translator = FakeTranslator(
        answers={
            "נילוס 200 גר": "Nilos 200 gr",
            "אבוקדו ישראל": "Avocado Israel",
        }
    )

    summary, rows = ProductNameTranslationJob(repository, translator).run_hebrew_sample(
        limit=20
    )

    assert translator.calls == ["נילוס 200 גר", "אבוקדו ישראל"]
    assert overwritten == [(14, "Nilos 200 gr"), (2003, "Avocado Israel")]
    assert summary.attempted == 2
    assert summary.saved == 2
    assert rows[0].item_name == "נילוס 200 גר"
    assert rows[0].item_name_en_after == "Nilos 200 gr"
