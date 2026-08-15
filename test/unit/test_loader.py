from src.database_loader.loader import (
    clear_staging,
    load_product_prices,
    load_products,
)


def test_load_products_upserts_from_staging(patch_loader_connection) -> None:
    _, cursor = patch_loader_connection
    cursor.fetchone_value = (12,)

    load_products()

    insert_sql, _ = cursor.executed[0]
    count_sql, _ = cursor.executed[1]

    assert "INSERT INTO grocery.products" in insert_sql
    assert "ON CONFLICT (item_code)" in insert_sql
    assert "SELECT COUNT(*)" in count_sql
    assert "FROM grocery.products" in count_sql


def test_load_product_prices_upserts_from_staging(patch_loader_connection) -> None:
    _, cursor = patch_loader_connection
    cursor.fetchone_value = (20,)

    load_product_prices()

    insert_sql, _ = cursor.executed[0]
    count_sql, _ = cursor.executed[1]

    assert "INSERT INTO grocery.product_prices" in insert_sql
    assert "ON CONFLICT" in insert_sql
    assert "FROM grocery.product_prices" in count_sql


def test_clear_staging_truncates_staging_table(patch_loader_connection) -> None:
    _, cursor = patch_loader_connection

    clear_staging()

    sql, _ = cursor.executed[0]
    assert "TRUNCATE TABLE grocery.products_staging" in sql
