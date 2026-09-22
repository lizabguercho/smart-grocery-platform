/*
CHAIN PRICES TABLE

Purpose:
Create a smaller analytical table containing one representative
price for each comparable product within each supermarket chain.

A product is considered comparable when the same item_code appears
in at least two supermarket chains.

Because the price of the same product can vary between stores within
a chain, the median store price is used as the representative
chain-level price.

This table will be used for cross-chain price comparison and can
later be included in the shared remote analytical database.
*/

CREATE TABLE grocery.chain_prices (
    item_code BIGINT,
    chain_id BIGINT,
    median_price NUMERIC(10,2),

    PRIMARY KEY (item_code, chain_id),
    FOREIGN KEY (item_code)
        REFERENCES grocery.products(item_code)
);

-- Remove the old calculated chain prices.
-- We rebuild the entire table from the latest available price data.
TRUNCATE TABLE grocery.chain_prices;


-- Step 1:
-- Find products that appear in at least two supermarket chains.
WITH comparable_products AS (
    SELECT
        lp.item_code
    FROM grocery.latest_product_prices lp
    GROUP BY lp.item_code
    HAVING COUNT(DISTINCT lp.chain_id) >= 2
),

-- Step 2:
-- Calculate one representative price for each product in each chain.
-- Median is used because the same product may have different prices
-- across stores belonging to the same chain.
calculated_chain_prices AS (
    SELECT
        lp.item_code,
        lp.chain_id,
        PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY lp.item_price) AS median_price
    FROM grocery.latest_product_prices lp
    JOIN comparable_products cp
        ON lp.item_code = cp.item_code
    WHERE lp.item_price > 0
    GROUP BY
        lp.item_code,
        lp.chain_id
)

-- Step 3:
-- Save the calculated results into the permanent analytical table.
INSERT INTO grocery.chain_prices (
    item_code,
    chain_id,
    median_price
)
SELECT
    item_code,
    chain_id,
    median_price
FROM calculated_chain_prices;

