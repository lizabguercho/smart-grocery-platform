CREATE VIEW grocery.analysis_products AS
SELECT
    p.item_code,
    p.item_name,
    p.manufacture_name,
    p.manufacture_item_description,
    p.unit_qty,
    p.quantity,
    p.unit_of_measure
FROM grocery.products p
WHERE p.item_code IN (
    SELECT item_code
    FROM grocery.latest_product_prices
    GROUP BY item_code
    HAVING COUNT(DISTINCT chain_id) >= 2
);

SELECT *
FROM grocery.analysis_products
LIMIT 20;

SELECT COUNT(*)
FROM grocery.analysis_products;

SELECT
    item_code,
    COUNT(*)
FROM grocery.analysis_products
GROUP BY item_code
HAVING COUNT(*) > 1;
