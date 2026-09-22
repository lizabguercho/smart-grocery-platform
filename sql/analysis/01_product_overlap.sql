-- ============================================================
-- PRODUCT OVERLAP ANALYSIS
-- ============================================================
-- Goal:
-- Understand how much of the product assortment can be
-- directly compared across Shufersal, Rami Levy and Victory
-- using item_code.
-- ==================

-- 1. Number of distinct products per chain

SELECT
    chain_id,
    COUNT(DISTINCT item_code) AS number_of_products
FROM grocery.product_prices
GROUP BY chain_id
ORDER BY number_of_products DESC;

-- 2. Number of products shared by at least two chains
SELECT COUNT(*) AS shared_products
FROM (
    SELECT item_code
    FROM grocery.product_prices
    GROUP BY item_code
    HAVING COUNT(DISTINCT chain_id) > 1
) AS shared_products;

-- 3. Product distribution by number of chains

SELECT
    number_of_chains,
    COUNT(*) AS number_of_products
FROM (
    SELECT
        item_code,
        COUNT(DISTINCT chain_id) AS number_of_chains
    FROM grocery.product_prices
    GROUP BY item_code
) AS product_chain_counts
GROUP BY number_of_chains
ORDER BY number_of_chains;

-- 4. Product overlap using latest prices

SELECT
    number_of_chains,
    COUNT(*) AS number_of_products
FROM (
    SELECT
        item_code,
        COUNT(DISTINCT chain_id) AS number_of_chains
    FROM grocery.latest_product_prices
    GROUP BY item_code
) AS product_chain_counts
GROUP BY number_of_chains
ORDER BY number_of_chains;
