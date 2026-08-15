import pytest

from src.database_loader.validation import (
    validate_product_prices,
    validate_staging,
)


def test_validate_staging_passes_when_no_invalid_rows(
    patch_validation_connection,
) -> None:
    _, cursor = patch_validation_connection
    cursor.fetchone_value = (0,)

    validate_staging()

    sql, _ = cursor.executed[0]
    assert "FROM grocery.products_staging" in sql
    assert "item_code IS NULL" in sql


def test_validate_staging_raises_when_invalid_rows_exist(
    patch_validation_connection,
) -> None:
    _, cursor = patch_validation_connection
    cursor.fetchone_value = (3,)

    with pytest.raises(ValueError, match="3 invalid rows"):
        validate_staging()


def test_validate_product_prices_passes_when_no_orphans(
    patch_validation_connection,
) -> None:
    _, cursor = patch_validation_connection
    cursor.fetchone_value = (0,)

    validate_product_prices()

    sql, _ = cursor.executed[0]
    assert "FROM grocery.product_prices" in sql
    assert "LEFT JOIN grocery.products" in sql


def test_validate_product_prices_raises_when_orphans_exist(
    patch_validation_connection,
) -> None:
    _, cursor = patch_validation_connection
    cursor.fetchone_value = (4,)

    with pytest.raises(ValueError, match="4 prices"):
        validate_product_prices()
