-- Analysis table: comparable prices + SuperCompare category.
-- One row per barcode that appears in at least two chains AND in SuperCompare.
--
-- The Python export writes the same join to:
--   data/processed/price_comparison_with_categories.csv
-- SuperCompare labels currently live in that crawl CSV, not yet in
-- grocery.product_classification. After labels are promoted, this view
-- is the SQL equivalent:

CREATE OR REPLACE VIEW grocery.price_comparison_with_categories AS
SELECT
    pc.item_code,
    p.item_name,
    cl.category,
    cl.subcategory,
    cl.include_in_analysis,
    cl.classification_method,
    pc.shufersal_price,
    pc.rami_levy_price,
    pc.victory_price,
    pc.cheapest_price,
    pc.cheapest_chain
FROM grocery.price_comparison AS pc
JOIN grocery.product_classification AS cl
    ON cl.item_code = pc.item_code
LEFT JOIN grocery.products AS p
    ON p.item_code = pc.item_code;
