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