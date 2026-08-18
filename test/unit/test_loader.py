from src.data_extraction.models import Store
from src.database_loader.loader import (
    clear_staging,
    load_product_prices,
    load_products,
    load_stores,
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


def test_load_stores_upserts_store_rows(patch_loader_connection, store: Store) -> None:
    _, cursor = patch_loader_connection
    cursor.fetchone_value = (1,)

    load_stores([store])

    insert_sql, rows = cursor.executed[0]
    count_sql, _ = cursor.executed[1]

    assert "INSERT INTO grocery.stores" in insert_sql
    assert "ON CONFLICT (chain_id, store_id)" in insert_sql
    assert rows == [
        (
            store.chain_id,
            store.store_id,
            store.chain_name,
            store.sub_chain_id,
            store.sub_chain_name,
            store.bikoret_no,
            store.store_type,
            store.store_name,
            store.address,
            store.city,
            store.zip_code,
            store.source_file,
            store.extraction_date,
        )
    ]
    assert "FROM grocery.stores" in count_sql


def test_load_stores_skips_rows_missing_keys(
    patch_loader_connection, store: Store
) -> None:
    _, cursor = patch_loader_connection
    cursor.fetchone_value = (0,)
    incomplete = Store(
        chain_id=None,
        chain_name=store.chain_name,
        sub_chain_id=store.sub_chain_id,
        sub_chain_name=store.sub_chain_name,
        store_id=store.store_id,
        bikoret_no=store.bikoret_no,
        store_type=store.store_type,
        store_name=store.store_name,
        address=store.address,
        city=store.city,
        zip_code=store.zip_code,
        source_file=store.source_file,
        extraction_date=store.extraction_date,
    )

    load_stores([incomplete])

    insert_sql, rows = cursor.executed[0]
    assert "INSERT INTO grocery.stores" in insert_sql
    assert rows == []
