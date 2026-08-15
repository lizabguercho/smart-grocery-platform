-- Load historical product prices from the staging table

-- Load historical product prices from the staging table

INSERT INTO grocery.product_prices (
    item_code,
    store_id,
    item_price,
    unit_of_measure_price,
    price_update_time,
    last_sale_date_time,
    item_status,
    allow_discount,
    chain_id,
    sub_chain_id,
    source_file,
    extraction_date
)
SELECT DISTINCT ON (
    chain_id,
    store_id,
    item_code,
    extraction_date
)
    item_code,
    store_id,
    item_price,
    unit_of_measure_price,
    price_update_time,
    last_sale_date_time,
    item_status,
    allow_discount,
    chain_id,
    sub_chain_id,
    source_file,
    extraction_date
FROM grocery.products_staging
WHERE item_code IS NOT NULL
  AND store_id IS NOT NULL
  AND chain_id IS NOT NULL
  AND extraction_date IS NOT NULL
ORDER BY
    chain_id,
    store_id,
    item_code,
    extraction_date,
    source_file DESC

ON CONFLICT (
    chain_id,
    store_id,
    item_code,
    extraction_date
)
DO UPDATE SET
    item_price = EXCLUDED.item_price,
    unit_of_measure_price = EXCLUDED.unit_of_measure_price,
    price_update_time = EXCLUDED.price_update_time,
    last_sale_date_time = EXCLUDED.last_sale_date_time,
    item_status = EXCLUDED.item_status,
    allow_discount = EXCLUDED.allow_discount,
    sub_chain_id = EXCLUDED.sub_chain_id,
    source_file = EXCLUDED.source_file;