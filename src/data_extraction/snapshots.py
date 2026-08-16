from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from src.data_extraction.data_extraction_config import (
    GZIP_EXTENSION,
    PRICE_FULL_FILENAME_MIN_PARTS,
    PRICE_FULL_FILENAME_PREFIX,
)
from src.etl.constants import SNAPSHOT_SELECTION_MESSAGE

T = TypeVar("T")


@dataclass(frozen=True)
class DailySnapshot(Generic[T]):
    store_id: str
    date: str
    time: str
    payload: T


def parse_price_full_filename(name: str) -> tuple[str, str, str] | None:
    """Return (store_id, date, time) from a PriceFull filename, or None."""
    # Expected: PriceFull{chain}-{sub}-{store}-{YYYYMMDD}-{HHMMSS}.gz
    lowered = name.lower()
    if not lowered.startswith(PRICE_FULL_FILENAME_PREFIX) or not lowered.endswith(
        GZIP_EXTENSION
    ):
        return None

    stem = name[: -len(GZIP_EXTENSION)]
    parts = stem.split("-")
    if len(parts) < PRICE_FULL_FILENAME_MIN_PARTS:
        return None

    store_id = parts[-3]
    date = parts[-2]
    time = parts[-1]
    return store_id, date, time


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
