"""Victory PriceFull, Stores, and PromoFull file downloader via laibcatalog HTTP API."""

from __future__ import annotations

from pathlib import Path

import requests

from src.data_extraction.data_extraction_config import (
    DOWNLOAD_CHUNK_SIZE_BYTES,
    PRICE_FULL_FILE_LABEL,
    PROMO_FULL_FILE_LABEL,
    SKIP_EXISTING_DOWNLOADS,
    STORES_FILE_LABEL,
    VICTORY_API_TIMEOUT_SECONDS,
    VICTORY_BASE_URL,
    VICTORY_BRANCH_NUMBER_KEY,
    VICTORY_CHAIN_ID,
    VICTORY_DOWNLOAD_PATH_PREFIX,
    VICTORY_DOWNLOAD_TIMEOUT_SECONDS,
    VICTORY_EDI_PARAM,
    VICTORY_FILE_DATE_KEY,
    VICTORY_FILE_NAME_KEY,
    VICTORY_FILE_TYPE_KEY,
    VICTORY_FILES_API_PATH,
    VICTORY_PRICE_FULL_FILE_TYPE,
    VICTORY_PRICE_FULL_RAW_DATA_DIR,
    VICTORY_PROMO_FULL_FILE_TYPE,
    VICTORY_PROMO_FULL_RAW_DATA_DIR,
    VICTORY_STORES_FILE_TYPE,
    VICTORY_STORES_RAW_DATA_DIR,
)
from src.data_extraction.snapshots import DailySnapshot, select_latest_daily_snapshots
from src.etl.constants import DEFAULT_MAX_FILES


def _list_files_by_type(file_type: str) -> list[dict]:
    """Return Victory API entries whose ``fileType`` matches ``file_type``."""
    response = requests.get(
        f"{VICTORY_BASE_URL}{VICTORY_FILES_API_PATH}",
        params={VICTORY_EDI_PARAM: VICTORY_CHAIN_ID},
        timeout=VICTORY_API_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    files = response.json()
    matched_files = []
    for entry in files:
        entry_type = str(entry.get(VICTORY_FILE_TYPE_KEY, "")).lower()
        if entry_type == file_type:
            matched_files.append(entry)

    return matched_files


def list_price_full_files() -> list[dict]:
    """Return all PriceFull file entries from the Victory API."""
    return _list_files_by_type(VICTORY_PRICE_FULL_FILE_TYPE)


def list_store_files() -> list[dict]:
    """Return all Stores file entries from the Victory API."""
    return _list_files_by_type(VICTORY_STORES_FILE_TYPE)


def list_promo_full_files() -> list[dict]:
    """Return all PromoFull file entries from the Victory API."""
    return _list_files_by_type(VICTORY_PROMO_FULL_FILE_TYPE)


def _snapshots_from_entries(
    entries: list[dict],
) -> list[DailySnapshot[dict]]:
    snapshots: list[DailySnapshot[dict]] = []
    for entry in entries:
        file_date = entry.get(VICTORY_FILE_DATE_KEY) or ""
        if " " not in file_date:
            continue

        date_text, time_text = file_date.split(" ", 1)
        store_id = entry.get(VICTORY_BRANCH_NUMBER_KEY)
        if store_id is None:
            continue

        snapshots.append(
            DailySnapshot(
                store_id=str(store_id),
                date=date_text,
                time=time_text,
                payload=entry,
            )
        )
    return snapshots


def select_latest_daily_snapshot_entries(
    entries: list[dict],
) -> list[dict]:
    """Keep the latest file per store for the latest available date."""
    selected = select_latest_daily_snapshots(_snapshots_from_entries(entries))
    return [snapshot.payload for snapshot in selected]


def _download_selected_files(
    *,
    entries: list[dict],
    output_dir: Path,
    file_label: str,
    max_files: int | None,
    skip_existing: bool,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_files = select_latest_daily_snapshot_entries(entries)

    if max_files is not None:
        selected_files = selected_files[:max_files]

    print(
        f"Found {len(selected_files)} {file_label} file(s) to download.",
        flush=True,
    )

    downloaded_files: list[Path] = []

    for entry in selected_files:
        remote_name = entry[VICTORY_FILE_NAME_KEY]
        output_path = output_dir / remote_name

        if skip_existing and output_path.exists():
            print(f"Skipping existing file: {output_path.name}", flush=True)
            downloaded_files.append(output_path)
            continue

        download_url = (
            f"{VICTORY_BASE_URL}{VICTORY_DOWNLOAD_PATH_PREFIX}"
            f"/{VICTORY_CHAIN_ID}/{remote_name}"
        )
        print(f"Downloading {remote_name}...", flush=True)

        with requests.get(
            download_url,
            timeout=VICTORY_DOWNLOAD_TIMEOUT_SECONDS,
            stream=True,
        ) as response:
            response.raise_for_status()
            with output_path.open("wb") as file:
                for chunk in response.iter_content(
                    chunk_size=DOWNLOAD_CHUNK_SIZE_BYTES
                ):
                    if chunk:
                        file.write(chunk)

        downloaded_files.append(output_path)

    return downloaded_files


def download_price_full_files(
    *,
    max_files: int | None = DEFAULT_MAX_FILES,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    """Download PriceFull `.gz` files into ``data/raw/price_full/victory``.

    Selects the latest snapshot per store for the latest available date.
    ``max_files`` limits how many stores are downloaded (development use).
    """
    return _download_selected_files(
        entries=list_price_full_files(),
        output_dir=VICTORY_PRICE_FULL_RAW_DATA_DIR,
        file_label=PRICE_FULL_FILE_LABEL,
        max_files=max_files,
        skip_existing=skip_existing,
    )


def download_store_files(
    *,
    max_files: int | None = DEFAULT_MAX_FILES,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    """Download Stores `.gz` files into ``data/raw/stores/victory``.

    Selects the latest snapshot per store for the latest available date.
    ``max_files`` limits how many files are downloaded (development use).
    """
    return _download_selected_files(
        entries=list_store_files(),
        output_dir=VICTORY_STORES_RAW_DATA_DIR,
        file_label=STORES_FILE_LABEL,
        max_files=max_files,
        skip_existing=skip_existing,
    )


def download_promo_full_files(
    *,
    max_files: int | None = DEFAULT_MAX_FILES,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    """Download PromoFull `.gz` files into ``data/raw/promo_full/victory``.

    Selects the latest snapshot per store for the latest available date.
    ``max_files`` limits how many stores are downloaded (development use).
    """
    return _download_selected_files(
        entries=list_promo_full_files(),
        output_dir=VICTORY_PROMO_FULL_RAW_DATA_DIR,
        file_label=PROMO_FULL_FILE_LABEL,
        max_files=max_files,
        skip_existing=skip_existing,
    )
