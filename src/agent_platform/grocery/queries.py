"""SQL used by the grocery tools.

Every statement is a named constant and every value is passed as a `%s`
parameter, per docs/client-server-architecture.md. There is no free-form SQL
tool, so the agent can only run the statements defined here.

A note on `LEAST`: PostgreSQL's `LEAST` skips NULL arguments, so
`LEAST(shufersal_price, rami_levy_price, victory_price)` is the lowest price
among the chains that actually stock the product. The cheapest chain is derived
from these price columns rather than from `price_comparison.cheapest_chain`,
because that column is a display label that folds ties into strings such as
'Shufersal & Rami Levy' and 'All three'.
"""

from __future__ import annotations

FIND_PRODUCTS_SQL = """
SELECT
    p.item_code,
    p.item_name,
    p.manufacture_name,
    (pc.item_code IS NOT NULL) AS is_comparable
FROM grocery.products AS p
LEFT JOIN grocery.price_comparison AS pc
    ON pc.item_code = p.item_code
WHERE p.item_name ILIKE %s
ORDER BY (pc.item_code IS NOT NULL) DESC, length(p.item_name), p.item_name
LIMIT %s
"""

COMPARE_PRODUCT_PRICES_SQL = """
SELECT
    pc.item_code,
    p.item_name,
    p.manufacture_name,
    pc.shufersal_price,
    pc.rami_levy_price,
    pc.victory_price,
    LEAST(pc.shufersal_price, pc.rami_levy_price, pc.victory_price) AS best_price,
    GREATEST(pc.shufersal_price, pc.rami_levy_price, pc.victory_price) AS worst_price
FROM grocery.price_comparison AS pc
LEFT JOIN grocery.products AS p
    ON p.item_code = pc.item_code
WHERE pc.item_code = %s
"""

CHEAPEST_CHAIN_SUMMARY_SQL = """
WITH scored AS (
    SELECT
        shufersal_price,
        rami_levy_price,
        victory_price,
        LEAST(shufersal_price, rami_levy_price, victory_price) AS best_price,
        (shufersal_price IS NOT NULL)::int
            + (rami_levy_price IS NOT NULL)::int
            + (victory_price IS NOT NULL)::int AS available_chains
    FROM grocery.price_comparison
),
flagged AS (
    SELECT
        COALESCE(shufersal_price = best_price, false) AS shufersal_best,
        COALESCE(rami_levy_price = best_price, false) AS rami_levy_best,
        COALESCE(victory_price = best_price, false) AS victory_best
    FROM scored
    WHERE best_price IS NOT NULL
      AND available_chains >= %s
),
counted AS (
    SELECT
        shufersal_best,
        rami_levy_best,
        victory_best,
        shufersal_best::int + rami_levy_best::int + victory_best::int AS winners
    FROM flagged
)
SELECT
    COUNT(*) AS products,
    COUNT(*) FILTER (WHERE winners = 1 AND shufersal_best) AS shufersal_outright,
    COUNT(*) FILTER (WHERE winners = 1 AND rami_levy_best) AS rami_levy_outright,
    COUNT(*) FILTER (WHERE winners = 1 AND victory_best) AS victory_outright,
    COUNT(*) FILTER (WHERE shufersal_best) AS shufersal_best_or_tied,
    COUNT(*) FILTER (WHERE rami_levy_best) AS rami_levy_best_or_tied,
    COUNT(*) FILTER (WHERE victory_best) AS victory_best_or_tied,
    COUNT(*) FILTER (WHERE winners > 1) AS tied_products
FROM counted
"""

CATEGORY_PRICE_SUMMARY_SQL = """
WITH scored AS (
    SELECT
        pcl.category,
        pc.cheapest_price,
        pc.shufersal_price,
        pc.rami_levy_price,
        pc.victory_price,
        LEAST(pc.shufersal_price, pc.rami_levy_price, pc.victory_price) AS best_price
    FROM grocery.price_comparison AS pc
    JOIN grocery.product_classification AS pcl
        ON pcl.item_code = pc.item_code
    WHERE pcl.include_in_analysis
      AND pcl.category IS NOT NULL
      AND (%s::text IS NULL OR pcl.category = %s::text)
),
flagged AS (
    SELECT
        category,
        cheapest_price,
        COALESCE(shufersal_price = best_price, false) AS shufersal_best,
        COALESCE(rami_levy_price = best_price, false) AS rami_levy_best,
        COALESCE(victory_price = best_price, false) AS victory_best
    FROM scored
    WHERE best_price IS NOT NULL
)
SELECT
    category,
    COUNT(*) AS products,
    COUNT(*) FILTER (WHERE shufersal_best) AS shufersal_best_or_tied,
    COUNT(*) FILTER (WHERE rami_levy_best) AS rami_levy_best_or_tied,
    COUNT(*) FILTER (WHERE victory_best) AS victory_best_or_tied,
    ROUND(AVG(cheapest_price), 2) AS average_cheapest_price
FROM flagged
GROUP BY category
ORDER BY products DESC, category
LIMIT %s
"""

DATABASE_OVERVIEW_SQL = """
SELECT
    (SELECT COUNT(*) FROM grocery.products) AS products,
    (SELECT COUNT(*) FROM grocery.price_comparison) AS comparable_products,
    (
        SELECT COUNT(*)
        FROM grocery.price_comparison
        WHERE shufersal_price IS NOT NULL
          AND rami_levy_price IS NOT NULL
          AND victory_price IS NOT NULL
    ) AS products_in_all_three_chains,
    (
        SELECT COUNT(*)
        FROM grocery.product_classification
        WHERE include_in_analysis
    ) AS classified_products,
    (SELECT COUNT(*) FROM grocery.stores) AS stores
"""

AVAILABLE_CATEGORIES_SQL = """
SELECT DISTINCT category
FROM grocery.product_classification
WHERE include_in_analysis
  AND category IS NOT NULL
ORDER BY category
"""
