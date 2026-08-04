-- ==========================================
-- Smart Grocery Platform
-- Inspection Queries
-- ==========================================


-- List all tables

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = 'grocery'
ORDER BY table_name;


-- List all indexes

SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'grocery'
ORDER BY indexname;





