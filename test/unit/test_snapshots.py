from __future__ import annotations

from src.data_extraction.snapshots import (
    DailySnapshot,
    parse_price_full_filename,
    select_latest_daily_snapshots,
)


def test_parse_price_full_filename_returns_store_date_and_time() -> None:
    parsed = parse_price_full_filename(
        "PriceFull7290027600007-001-001-20260722-030000.gz"
    )

    assert parsed == ("001", "20260722", "030000")


def test_parse_price_full_filename_rejects_non_price_full_names() -> None:
    assert (
        parse_price_full_filename("PromoFull7290027600007-001-001-20260722-030000.gz")
        is None
    )
    assert (
        parse_price_full_filename("PriceFull7290027600007-001-001-20260722.xml") is None
    )


def test_select_latest_daily_snapshots_returns_empty_for_no_input() -> None:
    assert select_latest_daily_snapshots([]) == []


def test_select_latest_daily_snapshots_keeps_latest_time_per_store() -> None:
    snapshots = [
        DailySnapshot("001", "20260721", "230000", "previous-day"),
        DailySnapshot("001", "20260722", "010000", "earlier"),
        DailySnapshot("001", "20260722", "030000", "latest"),
        DailySnapshot("002", "20260722", "040000", "store-2"),
    ]

    selected = select_latest_daily_snapshots(snapshots)

    assert [snapshot.payload for snapshot in selected] == ["latest", "store-2"]
