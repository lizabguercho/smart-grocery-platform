"""Read and write `grocery.products` for English names.

Hebrew `item_name` is never updated. We only add/fill `item_name_en`.
"""

from __future__ import annotations

from dataclasses import dataclass
from src.product_translation.exclusions import exclusion_like_patterns
from src.product_translation.config import SAMPLE_BATCH_SIZE, TEST_BATCH_SIZE
from src.product_translation.exclusions import exclusion_like_patterns
from src.product_translation.exclusions import exclusion_like_patterns
ADD_ENGLISH_NAME_COLUMN_SQL = """
ALTER TABLE grocery.products
    ADD COLUMN IF NOT EXISTS item_name_en TEXT;
"""

FETCH_UNTRANSLATED_SQL = """
SELECT
    item_code,
    item_name
FROM grocery.products
WHERE item_name IS NOT NULL
  AND btrim(item_name) <> ''
  AND (item_name_en IS NULL OR btrim(item_name_en) = '')
  AND NOT (
      item_name ILIKE ANY(%s)
  )
ORDER BY item_code
LIMIT %s;
"""

SAVE_ENGLISH_NAME_SQL = """
UPDATE grocery.products
SET item_name_en = %s
WHERE item_code = %s
  AND (item_name_en IS NULL OR btrim(item_name_en) = '');
"""

FETCH_RANDOM_HEBREW_PRODUCTS_SQL = """
SELECT
    item_code,
    item_name
FROM grocery.products
WHERE item_name IS NOT NULL
  AND btrim(item_name) <> ''
  AND item_name ~ '[א-ת]'
  AND NOT (item_name ILIKE ANY(%s))
ORDER BY random()
LIMIT %s;
"""

FETCH_TRANSLATED_SQL = """
SELECT
    item_code,
    item_name,
    item_name_en
FROM grocery.products
WHERE item_name IS NOT NULL
  AND btrim(item_name) <> ''
  AND item_name_en IS NOT NULL
  AND btrim(item_name_en) <> ''
ORDER BY item_code;
"""

OVERWRITE_ENGLISH_NAME_SQL = """
UPDATE grocery.products
SET item_name_en = %s
WHERE item_code = %s;
"""


@dataclass(frozen=True)
class ProductToTranslate:
    item_code: int
    item_name: str


@dataclass(frozen=True)
class TranslatedProduct:
    item_code: int
    item_name: str
    item_name_en: str


class ProductTranslationRepository:
    """Small SQL helper around one open PostgreSQL connection."""

    def __init__(self, connection) -> None:
        self._connection = connection

    def ensure_english_name_column(self) -> None:
        """Add item_name_en if this database was created before the column existed."""

        with self._connection.cursor() as cursor:
            cursor.execute(ADD_ENGLISH_NAME_COLUMN_SQL)
        self._connection.commit()

    def fetch_products_missing_english_name(
        self, limit: int = TEST_BATCH_SIZE
    ) -> list[ProductToTranslate]:
        """Skip rows that already have item_name_en; take the next `limit` names."""
        patterns = exclusion_like_patterns()
        with self._connection.cursor() as cursor:
            cursor.execute(FETCH_UNTRANSLATED_SQL, (patterns,limit,))
            rows = cursor.fetchall()
        return [
            ProductToTranslate(item_code=row[0], item_name=row[1]) for row in rows
        ]

    def fetch_hebrew_product_names(
        self, limit: int = SAMPLE_BATCH_SIZE
    ) -> list[ProductToTranslate]:
        """Random Hebrew catalog names, skipping fee/voucher lines."""

        with self._connection.cursor() as cursor:
            cursor.execute(
                FETCH_RANDOM_HEBREW_PRODUCTS_SQL,
                (exclusion_like_patterns(), limit),
            )
            rows = cursor.fetchall()
        return [
            ProductToTranslate(item_code=row[0], item_name=row[1]) for row in rows
        ]

    def save_english_name(self, item_code: int, english_name: str) -> None:
        """Write the English name only when the column is still empty."""

        with self._connection.cursor() as cursor:
            cursor.execute(SAVE_ENGLISH_NAME_SQL, (english_name, item_code))
        self._connection.commit()

    def fetch_translated_products(self) -> list[TranslatedProduct]:
        """All rows that already have an English name (used to find failures)."""

        with self._connection.cursor() as cursor:
            cursor.execute(FETCH_TRANSLATED_SQL)
            rows = cursor.fetchall()
        return [
            TranslatedProduct(
                item_code=row[0],
                item_name=row[1],
                item_name_en=row[2],
            )
            for row in rows
        ]

    def overwrite_english_name(self, item_code: int, english_name: str) -> None:
        """Replace item_name_en after a prompt fix. Still never touches item_name."""

        with self._connection.cursor() as cursor:
            cursor.execute(OVERWRITE_ENGLISH_NAME_SQL, (english_name, item_code))
        self._connection.commit()
