from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from src.data_extraction.data_extraction_config import (
    GZIP_EXTENSION,
    PRICE_FULL_FILENAME_MIN_PARTS,
    PRICE_FULL_FILENAME_PREFIX,
    PROMO_FULL_FILENAME_MIN_PARTS,
    PROMO_FULL_FILENAME_PREFIX,
    RAMI_LEVY_CHAIN_ID,
    RAMI_LEVY_UNSUPPORTED_STORE_ID,
    STORES_FILENAME_MIN_PARTS,
    STORES_FILENAME_PREFIX,
    XML_EXTENSION,
)
from src.etl.constants import SNAPSHOT_SELECTION_MESSAGE

T = TypeVar("T")


@dataclass(frozen=True)
class DailySnapshot(Generic[T]):
    store_id: str
    date: str
    time: str
    payload: T


def parse_snapshot_filename(
    name: str,
    prefix: str,
    min_parts: int = PRICE_FULL_FILENAME_MIN_PARTS,
    suffixes: tuple[str, ...] = (GZIP_EXTENSION,),
) -> tuple[str, str, str] | None:
    """Return (store_id, date, time) from a snapshot filename, or None."""
    lowered = name.lower()
    if not lowered.startswith(prefix):
        return None
    suffix = next((item for item in suffixes if lowered.endswith(item)), None)
    if suffix is None:
        return None
    stem = name[: -len(suffix)]
    parts = stem.split("-")
    if len(parts) < min_parts:
        return None
    store_id = parts[-3]
    date = parts[-2]
    time = parts[-1]
    return store_id, date, time


def parse_price_full_filename(name: str) -> tuple[str, str, str] | None:
    return parse_snapshot_filename(name, PRICE_FULL_FILENAME_PREFIX)


def parse_stores_filename(name: str) -> tuple[str, str, str] | None:
    return parse_snapshot_filename(
        name,
        STORES_FILENAME_PREFIX,
        min_parts=STORES_FILENAME_MIN_PARTS,
        suffixes=(GZIP_EXTENSION, XML_EXTENSION),
    )


def parse_promo_full_filename(name: str) -> tuple[str, str, str] | None:
    return parse_snapshot_filename(
        name,
        PROMO_FULL_FILENAME_PREFIX,
        min_parts=PROMO_FULL_FILENAME_MIN_PARTS,
    )


def is_unsupported_rami_levy_store_id(store_id: str | None) -> bool:
    if store_id is None:
        return False
    unsupported = RAMI_LEVY_UNSUPPORTED_STORE_ID.strip().lstrip("0")
    return store_id.strip().lstrip("0") == unsupported


def is_unsupported_rami_levy_promo_filename(name: str) -> bool:
    lowered = name.lower()
    if not lowered.startswith(PROMO_FULL_FILENAME_PREFIX + RAMI_LEVY_CHAIN_ID):
        return False
    parsed = parse_promo_full_filename(name)
    if parsed is None:
        return False
    store_id, _, _ = parsed
    return is_unsupported_rami_levy_store_id(store_id)


def select_latest_daily_snapshots(
    snapshots: list[DailySnapshot[T]],
) -> list[DailySnapshot[T]]:
    """Keep the latest snapshot per store for the latest available date."""
    if not snapshots:
        return []

    latest_date = max(snapshot.date for snapshot in snapshots)
    same_day_snapshots = [
        snapshot for snapshot in snapshots if snapshot.date == latest_date
    ]

    latest_by_store: dict[str, DailySnapshot[T]] = {}
    for snapshot in same_day_snapshots:
        current = latest_by_store.get(snapshot.store_id)
        if current is None or snapshot.time > current.time:
            latest_by_store[snapshot.store_id] = snapshot

    selected = [latest_by_store[store_id] for store_id in sorted(latest_by_store)]
    print(
        SNAPSHOT_SELECTION_MESSAGE.format(
            latest_date=latest_date,
            count=len(selected),
        ),
        flush=True,
    )
    return selected
