-- Add an English product-name column without touching the original Hebrew name.
-- Safe to run more than once (IF NOT EXISTS).

ALTER TABLE grocery.products
    ADD COLUMN IF NOT EXISTS item_name_en TEXT;
