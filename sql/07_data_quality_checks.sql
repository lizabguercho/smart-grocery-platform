-- Smart Grocery Platform
-- Data quality checks


-- 1. Count unique products

SELECT COUNT(*) AS total_products
FROM grocery.products;


-- 2. Count price records

SELECT COUNT(*) AS total_price_records
FROM grocery.product_prices;


-- 3. Check for duplicate products

SELECT
    item_code,
    COUNT(*) AS row_count
FROM grocery.products
GROUP BY item_code
HAVING COUNT(*) > 1;


-- 4. Check for duplicate price records

SELECT
    store_id,
    item_code,
    extraction_date,
    COUNT(*) AS row_count
FROM grocery.product_prices
GROUP BY
    store_id,
    item_code,
    extraction_date
HAVING COUNT(*) > 1;


-- 5. Check for prices without a matching product

SELECT COUNT(*) AS prices_without_product
FROM grocery.product_prices pp
LEFT JOIN grocery.products p
    ON pp.item_code = p.item_code
WHERE p.item_code IS NULL;


-- 6. Check for missing essential values

SELECT COUNT(*) AS rows_with_missing_values
FROM grocery.product_prices
WHERE item_code IS NULL
   OR store_id IS NULL
   OR extraction_date IS NULL
   OR item_price IS NULL;