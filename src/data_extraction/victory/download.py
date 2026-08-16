"""Victory PriceFull file downloader via laibcatalog HTTP API."""

from __future__ import annotations

from pathlib import Path

import requests

from src.data_extraction.data_extraction_config import (
    DOWNLOAD_CHUNK_SIZE_BYTES,
    SKIP_EXISTING_DOWNLOADS,
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
    VICTORY_RAW_DATA_DIR,
)
from src.data_extraction.snapshots import DailySnapshot, select_latest_daily_snapshots
from src.etl.constants import DEFAULT_MAX_FILES


def list_price_full_files() -> list[dict]:
    """Return all PriceFull file entries from the Victory API."""
    response = requests.get(
        f"{VICTORY_BASE_URL}{VICTORY_FILES_API_PATH}",
        params={VICTORY_EDI_PARAM: VICTORY_CHAIN_ID},
        timeout=VICTORY_API_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    files = response.json()

    price_full_files = []
    for entry in files:
        file_type = str(entry.get(VICTORY_FILE_TYPE_KEY, "")).lower()
        if file_type == VICTORY_PRICE_FULL_FILE_TYPE:
            price_full_files.append(entry)

    return price_full_files


def _snapshots_from_entries(
    price_full_files: list[dict],
) -> list[DailySnapshot[dict]]:
    snapshots: list[DailySnapshot[dict]] = []
    for entry in price_full_files:
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
    price_full_files: list[dict],
) -> list[dict]:
    """Keep the latest PriceFull file per store for the latest available date."""
    selected = select_latest_daily_snapshots(_snapshots_from_entries(price_full_files))
    return [snapshot.payload for snapshot in selected]


def download_price_full_files(
    *,
    max_files: int | None = DEFAULT_MAX_FILES,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    """Download PriceFull `.gz` files into ``data/raw/victory``.

    Selects the latest snapshot per store for the latest available date.
    ``max_files`` limits how many stores are downloaded (development use).
    """
    output_dir = VICTORY_RAW_DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    price_full_files = list_price_full_files()
    selected_files = select_latest_daily_snapshot_entries(price_full_files)

    if max_files is not None:
        selected_files = selected_files[:max_files]

    print(f"Found {len(selected_files)} PriceFull file(s) to download.", flush=True)

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
