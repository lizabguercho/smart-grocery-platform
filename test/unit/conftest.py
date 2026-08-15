from __future__ import annotations

from collections.abc import Iterator
from typing import Self
from unittest.mock import patch

import pytest

from src.data_extraction.models import PriceFullProduct


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
