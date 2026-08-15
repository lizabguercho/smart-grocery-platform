-- Load one row per unique product from the staging table

INSERT INTO grocery.products (
    item_code,
    item_name,
    manufacture_name,
    manufacture_country,
    manufacture_item_description,
    unit_qty,
    quantity,
    unit_of_measure,
    is_weighted,
    qty_in_package,
    item_type
)
SELECT DISTINCT ON (item_code)
    item_code,
    item_name,
    manufacture_name,
    manufacture_country,
    manufacture_item_description,
    unit_qty,
    quantity,
    unit_of_measure,
    is_weighted,
    qty_in_package,
    item_type
FROM grocery.products_staging
WHERE item_code IS NOT NULL
ORDER BY item_code, extraction_date DESC
ON CONFLICT (item_code) DO NOTHING;