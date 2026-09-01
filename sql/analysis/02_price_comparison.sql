-- Find exact products that are currently available in at least two supermarket chains.
-- Products are matched using item_code, so these comparisons refer to the same SKU.

SELECT
    item_code,
    COUNT(DISTINCT chain_id) AS number_of_chains
FROM grocery.latest_product_prices
GROUP BY item_code
HAVING COUNT(DISTINCT chain_id) >= 2
ORDER BY number_of_chains DESC;

-- Check whether the same product has different latest prices
-- across stores belonging to the same supermarket chain.

SELECT
    item_code,
    chain_id,
    COUNT(DISTINCT item_price) AS different_prices,
    MIN(item_price) AS lowest_price,
    MAX(item_price) AS highest_price
FROM grocery.latest_product_prices
GROUP BY
    item_code,
    chain_id
HAVING COUNT(DISTINCT item_price) > 1
ORDER BY different_prices DESC
LIMIT 20;

-- Calculate one representative price for each exact product in each chain.
-- Median is used because store prices can vary significantly and extreme
-- store prices could distort a simple average.

SELECT
    item_code,
    chain_id,
    PERCENTILE_CONT(0.5)
        WITHIN GROUP (ORDER BY item_price) AS median_price,
    MIN(item_price) AS lowest_price,
    MAX(item_price) AS highest_price,
    COUNT(DISTINCT store_id) AS number_of_stores
FROM grocery.latest_product_prices
WHERE item_price > 0
GROUP BY
    item_code,
    chain_id
ORDER BY
    item_code,
    chain_id;

WITH chain_prices AS (
    SELECT
        item_code,
        chain_id,
        PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY item_price) AS median_price,
        MIN(item_price) AS lowest_price,
        MAX(item_price) AS highest_price,
        COUNT(DISTINCT store_id) AS number_of_stores
    FROM grocery.latest_product_prices
    WHERE item_price > 0
    GROUP BY
        item_code,
        chain_id
)

SELECT
    cp.*,
    p.item_name
FROM chain_prices cp
JOIN grocery.products p
    ON cp.item_code = p.item_code
WHERE cp.item_code IN (
    SELECT item_code
    FROM chain_prices
    GROUP BY item_code
    HAVING COUNT(DISTINCT chain_id) >= 2
)
ORDER BY
    cp.item_code,
    cp.chain_id;

-- Put each chain's median price into its own column.
-- This gives us one row per product and makes direct comparison easier.

/*
PRICE COMPARISON BETWEEN SUPERMARKET CHAINS

Goal:
Compare the price of the exact same products across Shufersal,
Rami Levy and Victory.

Products are matched by item_code, so this analysis only compares
identical SKUs that appear in at least two supermarket chains.

Because the price of the same product can vary between stores within
one chain, the median store price is used as the representative
chain-level price. The median is less sensitive to unusually high
or low store prices than the average.
*/


-- Step 1:
-- Calculate one representative price for each product within each chain.
-- Each row produced here represents one item_code + one supermarket chain.

WITH chain_prices AS (
    SELECT
        item_code,
        chain_id,

        -- Median price across all stores in this chain that sell the product.
        PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY item_price) AS median_price

    FROM grocery.latest_product_prices

    -- Exclude invalid/non-positive prices from the comparison.
    WHERE item_price > 0

    GROUP BY
        item_code,
        chain_id
),


-- Step 2:
-- Transform the data so that each product has one row,
-- with a separate price column for each supermarket chain.
--
-- Example:
-- item A | Shufersal 10.90 | Rami Levy 9.90 | Victory 11.90

price_comparison AS (
    SELECT
        cp.item_code,
        p.item_name,

        -- Shufersal median price
        MAX(
            CASE
                WHEN cp.chain_id = 7290027600007
                THEN cp.median_price
            END
        ) AS shufersal_price,

        -- Rami Levy median price
        MAX(
            CASE
                WHEN cp.chain_id = 7290058140886
                THEN cp.median_price
            END
        ) AS rami_levy_price,

        -- Victory median price
        MAX(
            CASE
                WHEN cp.chain_id = 7290696200003
                THEN cp.median_price
            END
        ) AS victory_price

    FROM chain_prices cp

    -- Join products to add a readable product name.
    JOIN grocery.products p
        ON cp.item_code = p.item_code

    GROUP BY
        cp.item_code,
        p.item_name

    -- Only keep products that are available in at least two chains.
    -- A product available in only one chain cannot be used for
    -- an exact cross-chain price comparison.
    HAVING COUNT(DISTINCT cp.chain_id) >= 2
),


-- Step 3:
-- Find the lowest median price available for each product.
-- LEAST compares the available chain prices and returns the lowest one.

with_cheapest_price AS (
    SELECT
        *,
        LEAST(
            shufersal_price,
            rami_levy_price,
            victory_price
        ) AS cheapest_price

    FROM price_comparison
)


-- Step 4:
-- Identify which supermarket has the cheapest median price.
-- If two or more chains have exactly the same lowest price,
-- classify the result as a tie.

SELECT
    *,

    CASE
        -- Shufersal and Rami Levy have the same cheapest price.
        WHEN shufersal_price = cheapest_price
             AND rami_levy_price = cheapest_price
            THEN 'Tie'

        -- Shufersal and Victory have the same cheapest price.
        WHEN shufersal_price = cheapest_price
             AND victory_price = cheapest_price
            THEN 'Tie'

        -- Rami Levy and Victory have the same cheapest price.
        WHEN rami_levy_price = cheapest_price
             AND victory_price = cheapest_price
            THEN 'Tie'

        -- Otherwise identify the single cheapest chain.
        WHEN shufersal_price = cheapest_price
            THEN 'Shufersal'

        WHEN rami_levy_price = cheapest_price
            THEN 'Rami Levy'

        WHEN victory_price = cheapest_price
            THEN 'Victory'

    END AS cheapest_chain

FROM with_cheapest_price

ORDER BY item_code;
