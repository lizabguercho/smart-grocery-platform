-- Load historical product prices from the staging table

INSERT INTO grocery.product_prices (
    item_code,
    store_id,
    item_price,
    unit_of_measure_price,
    price_update_time,
    item_status,
    allow_discount,
    source_file,
    extraction_date
)
SELECT
    item_code,
    store_id,
    item_price,
    unit_of_measure_price,
    price_update_time,
    item_status,
    allow_discount,
    source_file,
    extraction_date
FROM grocery.shufersal_products_staging
WHERE item_code IS NOT NULL
  AND store_id IS NOT NULL
  AND extraction_date IS NOT NULL
ON CONFLICT (store_id, item_code, extraction_date) DO UPDATE
SET
    item_price = EXCLUDED.item_price,
    unit_of_measure_price = EXCLUDED.unit_of_measure_price,
    price_update_time = EXCLUDED.price_update_time,
    item_status = EXCLUDED.item_status,
    allow_discount = EXCLUDED.allow_discount,
    source_file = EXCLUDED.source_file;