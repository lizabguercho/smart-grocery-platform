from src.data_extraction.models import PriceFullProduct
from src.database_loader.loader import load_products_to_staging


def test_load_products_to_staging_truncates_and_inserts_mapped_rows(
    patch_loader_connection,
    product: PriceFullProduct,
) -> None:
    _, cursor = patch_loader_connection
    cursor.fetchone_value = (1,)

    load_products_to_staging([product])

    truncate_sql, _ = cursor.executed[0]
    insert_sql, rows = cursor.executed[1]
    count_sql, _ = cursor.executed[2]

    assert "TRUNCATE TABLE grocery.products_staging" in truncate_sql
    assert "INSERT INTO grocery.products_staging" in insert_sql
    assert "SELECT COUNT(*)" in count_sql
    assert rows == [
        (
            "7290001",
            "Milk 3%",
            "Tnuva",
            "IL",
            "Milk",
            "1",
            "1",
            "liter",
            "0",
            "1",
            "7.90",
            "7.90",
            "1",
            "1",
            "2026-07-22 03:00:00",
            None,
            "1",
            "001",
            "7290027600007",
            "001",
            "PriceFull7290027600007-001-001-20260722-030000.gz",
            "2026-07-22",
        )
    ]


def test_load_products_to_staging_inserts_empty_list(
    patch_loader_connection,
) -> None:
    _, cursor = patch_loader_connection

    load_products_to_staging([])

    _, rows = cursor.executed[1]
    assert rows == []
