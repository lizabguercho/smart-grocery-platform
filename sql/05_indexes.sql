-- ==========================================
-- Smart Grocery Platform
-- Database Indexes
-- ==========================================

-- Speed up searches by product
CREATE INDEX IF NOT EXISTS idx_product_prices_item_code
ON grocery.product_prices (item_code);

-- Speed up searches by store
CREATE INDEX IF NOT EXISTS idx_product_prices_store_id
ON grocery.product_prices (store_id);

-- Speed up searches by extraction date
CREATE INDEX IF NOT EXISTS idx_product_prices_extraction_date
ON grocery.product_prices (extraction_date);

-- Speed up promotion searches by store
CREATE INDEX IF NOT EXISTS idx_promotions_store_id
ON grocery.promotions (store_id);

-- Speed up promotion searches by extraction date
CREATE INDEX IF NOT EXISTS idx_promotions_extraction_date
ON grocery.promotions (extraction_date);

-- Speed up promotion item searches by product
CREATE INDEX IF NOT EXISTS idx_promotion_items_item_code
ON grocery.promotion_items (item_code);