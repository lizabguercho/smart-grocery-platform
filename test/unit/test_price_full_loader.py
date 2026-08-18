from __future__ import annotations

from unittest.mock import patch

from src.data_extraction.models import PriceFullProduct
from src.database_loader.price_full_loader import PriceFullLoader


def test_price_full_loader_runs_staging_validate_upsert_and_clear(
    product: PriceFullProduct,
) -> None:
    order: list[str] = []

    def track(name: str):
        def _side_effect(*args: object, **kwargs: object) -> None:
            order.append(name)

        return _side_effect

    with (
        patch(
            "src.database_loader.price_full_loader.load_products_to_staging",
            side_effect=track("load_products_to_staging"),
        ) as load_staging,
        patch(
            "src.database_loader.price_full_loader.validate_staging",
            side_effect=track("validate_staging"),
        ),
        patch(
            "src.database_loader.price_full_loader.load_products",
            side_effect=track("load_products"),
        ),
        patch(
            "src.database_loader.price_full_loader.load_product_prices",
            side_effect=track("load_product_prices"),
        ),
        patch(
            "src.database_loader.price_full_loader.validate_product_prices",
            side_effect=track("validate_product_prices"),
        ),
        patch(
            "src.database_loader.price_full_loader.clear_staging",
            side_effect=track("clear_staging"),
        ),
    ):
        PriceFullLoader().load([product])

    load_staging.assert_called_once_with([product])
    assert order == [
        "load_products_to_staging",
        "validate_staging",
        "load_products",
        "load_product_prices",
        "validate_product_prices",
        "clear_staging",
    ]
