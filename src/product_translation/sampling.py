"""Draw a random sample of Hebrew catalog names from grocery.products.

Read-only. Callers decide what to do with the rows: print them, or hand
them to the translation job.
"""

from __future__ import annotations

from src.product_translation.exclusions import exclusion_like_patterns
from src.product_translation.repository import ProductToTranslate

SAMPLE_HEBREW_PRODUCTS_SQL = """
SELECT
    item_code,
    item_name
FROM grocery.products
WHERE item_name IS NOT NULL
  AND btrim(item_name) <> ''
  AND item_name ~ '[א-ת]'
  AND NOT (item_name ILIKE ANY(%s))
  AND item_code <> ALL(%s)
ORDER BY random()
LIMIT %s;
"""


def sample_hebrew_products(
    connection,
    limit: int,
    seed: float | None = None,
    exclude_codes: list[str] | None = None,
) -> list[ProductToTranslate]:
    """Return up to `limit` random Hebrew names, skipping fee and voucher lines.

    `seed` (in [-1, 1]) makes the draw reproducible for a given catalog snapshot;
    `exclude_codes` removes products that were already drawn or inspected.
    """

    if limit < 1:
        raise ValueError("limit must be at least 1")
    with connection.cursor() as cursor:
        if seed is not None:
            cursor.execute("SELECT setseed(%s)", (seed,))
        cursor.execute(
            SAMPLE_HEBREW_PRODUCTS_SQL,
            (exclusion_like_patterns(), exclude_codes or [], limit),
        )
        rows = cursor.fetchall()
    return [ProductToTranslate(item_code=row[0], item_name=row[1]) for row in rows]
