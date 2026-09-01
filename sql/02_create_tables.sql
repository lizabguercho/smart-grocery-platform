-- ==========================================
-- Smart Grocery Platform
-- Create Tables
-- ==========================================

-- ==========================================
-- Products
-- One row per unique product
-- ==========================================

CREATE TABLE IF NOT EXISTS grocery.products (
    item_code BIGINT PRIMARY KEY,
    item_name TEXT,
    manufacture_name TEXT,
    manufacture_country TEXT,
    manufacture_item_description TEXT,
    unit_qty TEXT,
    quantity NUMERIC,
    unit_of_measure TEXT,
    is_weighted BOOLEAN,
    qty_in_package INTEGER,
    item_type INTEGER
);

-- ==========================================
-- Product Prices
-- Historical prices for each product in each
-- store on every extraction date
-- ==========================================

CREATE TABLE IF NOT EXISTS grocery.product_prices (
    item_code BIGINT NOT NULL,
    store_id INTEGER NOT NULL,
    item_price NUMERIC(10,2),
    unit_of_measure_price NUMERIC(10,2),
    price_update_time TIMESTAMP,
    last_sale_date_time TIMESTAMP,
    item_status INTEGER,
    allow_discount BOOLEAN,
    chain_id BIGINT NOT NULL,
    sub_chain_id INTEGER,
    source_file TEXT,
    extraction_date DATE NOT NULL,

    CONSTRAINT product_prices_pk
        PRIMARY KEY (chain_id, store_id, item_code, extraction_date),

    CONSTRAINT product_prices_product_fk
        FOREIGN KEY (item_code)
        REFERENCES grocery.products(item_code)
);

-- ==========================================
-- Shufersal Staging
-- Raw data imported directly from Shufersal
-- XML files before cleaning and normalization
-- ==========================================

CREATE TABLE IF NOT EXISTS grocery.products_staging (
    item_code BIGINT,
    item_name TEXT,
    manufacture_name TEXT,
    manufacture_country TEXT,
    manufacture_item_description TEXT,
    unit_qty TEXT,
    quantity NUMERIC,
    unit_of_measure TEXT,
    is_weighted BOOLEAN,
    qty_in_package INTEGER,
    item_price NUMERIC(10,2),
    unit_of_measure_price NUMERIC(10,2),
    allow_discount BOOLEAN,
    item_status INTEGER,
    price_update_time TIMESTAMP,
    last_sale_date_time TIMESTAMP,
    item_type INTEGER,
    store_id INTEGER,
    chain_id BIGINT,
    sub_chain_id INTEGER,
    source_file TEXT,
    extraction_date DATE
);

-- ==========================================
-- Stores
-- Latest known metadata for each store in a
-- chain. Re-runs update the existing row.
-- ==========================================

CREATE TABLE IF NOT EXISTS grocery.stores (
    chain_id BIGINT NOT NULL,
    store_id INTEGER NOT NULL,
    chain_name TEXT,
    sub_chain_id INTEGER,
    sub_chain_name TEXT,
    bikoret_no INTEGER,
    store_type INTEGER,
    store_name TEXT,
    address TEXT,
    city TEXT,
    zip_code TEXT,
    source_file TEXT,
    extraction_date DATE,

    CONSTRAINT stores_pk
        PRIMARY KEY (chain_id, store_id)
);


-- ==========================================
-- Promotions
-- One promotion in one store on one
-- extraction date. Re-runs update the row.
-- ==========================================

CREATE TABLE IF NOT EXISTS grocery.promotions (
    chain_id BIGINT NOT NULL,
    store_id INTEGER NOT NULL,
    promotion_id TEXT NOT NULL,
    extraction_date DATE NOT NULL,
    sub_chain_id INTEGER,
    bikoret_no INTEGER,
    promotion_description TEXT,
    promotion_start_date_time TIMESTAMP,
    promotion_end_date_time TIMESTAMP,
    promotion_start_hour TEXT,
    promotion_end_hour TEXT,
    promotion_update_time TIMESTAMP,
    allow_multiple_discounts BOOLEAN,
    club_id TEXT,
    min_no_of_item_offered NUMERIC,
    redemption_limit INTEGER,
    is_gift_item TEXT,
    additional_is_coupon BOOLEAN,
    additional_restrictions TEXT,
    remarks TEXT,
    promotion_days TEXT,
    source_file TEXT,

    CONSTRAINT promotions_pk
        PRIMARY KEY (chain_id, store_id, promotion_id, extraction_date)
);


-- ==========================================
-- Promotion Groups
-- One group inside a promotion. Group fields
-- such as MinPurchaseAmount live here.
-- ==========================================

CREATE TABLE IF NOT EXISTS grocery.promotion_groups (
    chain_id BIGINT NOT NULL,
    store_id INTEGER NOT NULL,
    promotion_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    extraction_date DATE NOT NULL,
    min_purchase_amount NUMERIC,
    discount_type TEXT,

    CONSTRAINT promotion_groups_pk
        PRIMARY KEY (chain_id, store_id, promotion_id, group_id, extraction_date),

    CONSTRAINT promotion_groups_promotion_fk
        FOREIGN KEY (chain_id, store_id, promotion_id, extraction_date)
        REFERENCES grocery.promotions (
            chain_id,
            store_id,
            promotion_id,
            extraction_date
        )
);


-- ==========================================
-- Promotion Items
-- Products mapped to a promotion group.
-- Item-level reward fields live here.
-- ==========================================

CREATE TABLE IF NOT EXISTS grocery.promotion_items (
    chain_id BIGINT NOT NULL,
    store_id INTEGER NOT NULL,
    promotion_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    item_code BIGINT NOT NULL,
    extraction_date DATE NOT NULL,
    item_type INTEGER,
    is_weighted BOOLEAN,
    reward_type TEXT,
    min_qty NUMERIC,
    max_qty NUMERIC,
    discounted_price NUMERIC(10,2),
    discounted_price_per_mida NUMERIC(10,2),
    discount_rate NUMERIC,

    CONSTRAINT promotion_items_pk
        PRIMARY KEY (
            chain_id,
            store_id,
            promotion_id,
            group_id,
            item_code,
            extraction_date
        ),

    CONSTRAINT promotion_items_group_fk
        FOREIGN KEY (
            chain_id,
            store_id,
            promotion_id,
            group_id,
            extraction_date
        )
        REFERENCES grocery.promotion_groups (
            chain_id,
            store_id,
            promotion_id,
            group_id,
            extraction_date
        )
);


