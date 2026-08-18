from __future__ import annotations

from src.data_extraction.snapshots import (
    DailySnapshot,
    is_unsupported_rami_levy_promo_filename,
    parse_price_full_filename,
    parse_promo_full_filename,
    parse_stores_filename,
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


def test_parse_stores_filename_accepts_four_part_chain_file() -> None:
    parsed = parse_stores_filename("Stores7290027600007-000-20260816-020.gz")

    assert parsed == ("000", "20260816", "020")


def test_parse_stores_filename_accepts_four_part_xml() -> None:
    parsed = parse_stores_filename("Stores7290058140886-000-20260816-050500.xml")

    assert parsed == ("000", "20260816", "050500")


def test_parse_stores_filename_accepts_packed_victory_datetime() -> None:
    parsed = parse_stores_filename("Stores7290696200003-000-20260816060100-060100.gz")

    assert parsed == ("000", "20260816060100", "060100")


def test_parse_stores_filename_accepts_five_part_name() -> None:
    parsed = parse_stores_filename("Stores7290027600007-000-000-20260722-030000.gz")

    assert parsed == ("000", "20260722", "030000")


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


def test_parse_promo_full_filename_returns_store_date_and_time() -> None:
    parsed = parse_promo_full_filename(
        "PromoFull7290027600007-001-001-20260816-030000.gz"
    )

    assert parsed == ("001", "20260816", "030000")


def test_parse_promo_full_filename_rejects_non_promo_full_names() -> None:
    assert (
        parse_promo_full_filename("PriceFull7290027600007-001-001-20260816-030000.gz")
        is None
    )


def test_is_unsupported_rami_levy_promo_filename_skips_store_039() -> None:
    assert is_unsupported_rami_levy_promo_filename(
        "PromoFull7290058140886-001-039-20260816-030000.gz"
    )
    assert is_unsupported_rami_levy_promo_filename(
        "PromoFull7290058140886-001-39-20260816-030000.gz"
    )
    assert not is_unsupported_rami_levy_promo_filename(
        "PromoFull7290058140886-001-001-20260816-030000.gz"
    )
    assert not is_unsupported_rami_levy_promo_filename(
        "PromoFull7290027600007-001-039-20260816-030000.gz"
    )
