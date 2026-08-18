from __future__ import annotations

from collections.abc import Iterator
from typing import Self
from unittest.mock import patch

import pytest

from src.data_extraction.models import (
    PriceFullProduct,
    Promotion,
    PromotionGroup,
    PromotionItem,
    Store,
)


class FakeCursor:
    def __init__(self, fetchone_value: object = (0,)) -> None:
        self.fetchone_value = fetchone_value
        self.executed: list[tuple[str, object]] = []

    def execute(self, sql: str, params: object = None) -> None:
        self.executed.append((sql, params))

    def executemany(self, sql: str, seq_of_params: object) -> None:
        self.executed.append((sql, seq_of_params))

    def fetchone(self) -> object:
        return self.fetchone_value

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> FakeCursor:
        return self._cursor

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


@pytest.fixture
def product() -> PriceFullProduct:
    return PriceFullProduct(
        item_code="7290001",
        item_name="Milk 3%",
        manufacture_name="Tnuva",
        manufacture_country="IL",
        manufacture_item_description="Milk",
        unit_qty="1",
        quantity="1",
        unit_of_measure="liter",
        is_weighted="0",
        qty_in_package="1",
        item_price="7.90",
        unit_of_measure_price="7.90",
        allow_discount="1",
        item_status="1",
        price_update_time="2026-07-22 03:00:00",
        last_sale_date_time=None,
        item_type="1",
        store_id="001",
        chain_id="7290027600007",
        sub_chain_id="001",
        source_file="PriceFull7290027600007-001-001-20260722-030000.gz",
        extraction_date="2026-07-22",
    )


@pytest.fixture
def store() -> Store:
    return Store(
        chain_id="7290027600007",
        chain_name="Shufersal",
        sub_chain_id="1",
        sub_chain_name="Shufersal Sheli",
        store_id="756",
        bikoret_no="7",
        store_type="1",
        store_name="Sheli Beer Yaakov",
        address="17 Yitzhak Shamir",
        city="2530",
        zip_code="7030336",
        source_file="Stores7290027600007-000-20260816-020.gz",
        extraction_date="2026-08-16",
    )


@pytest.fixture
def promotion() -> Promotion:
    return Promotion(
        chain_id="7290027600007",
        sub_chain_id="001",
        store_id="001",
        bikoret_no="1",
        source_file="PromoFull7290027600007-001-001-20260816-030000.gz",
        extraction_date="2026-08-16",
        promotion_id="100",
        promotion_description="Buy 2 get 1",
        promotion_start_date_time="2026-08-01 00:00:00",
        promotion_end_date_time="2026-08-31 23:59:00",
        promotion_start_hour="0000",
        promotion_end_hour="2359",
        promotion_update_time="2026-08-16 03:00:00",
        allow_multiple_discounts="1",
        club_id="0",
        min_no_of_item_offered="1",
        redemption_limit="0",
        is_gift_item="0",
        additional_is_coupon="0",
        additional_restrictions=None,
        remarks=None,
        promotion_days="1111111",
        groups=[
            PromotionGroup(
                group_id="1",
                min_purchase_amount="20",
                discount_type="1",
                items=[
                    PromotionItem(
                        item_code="123",
                        item_type="1",
                        is_weighted="0",
                        reward_type="1",
                        min_qty="1",
                        max_qty="10",
                        discounted_price="5.90",
                        discounted_price_per_mida="5.90",
                        discount_rate="10",
                    )
                ],
            )
        ],
    )


@pytest.fixture
def fake_db() -> tuple[FakeConnection, FakeCursor]:
    cursor = FakeCursor(fetchone_value=(0,))
    return FakeConnection(cursor), cursor


@pytest.fixture
def patch_loader_connection(
    fake_db: tuple[FakeConnection, FakeCursor],
) -> Iterator[tuple[FakeConnection, FakeCursor]]:
    connection, cursor = fake_db
    with patch(
        "src.database_loader.loader.get_connection",
        return_value=connection,
    ):
        yield connection, cursor


@pytest.fixture
def patch_validation_connection(
    fake_db: tuple[FakeConnection, FakeCursor],
) -> Iterator[tuple[FakeConnection, FakeCursor]]:
    connection, cursor = fake_db
    with patch(
        "src.database_loader.validation.get_connection",
        return_value=connection,
    ):
        yield connection, cursor
