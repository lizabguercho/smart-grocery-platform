"""Victory PriceFull file downloader via laibcatalog HTTP API."""

from __future__ import annotations

from pathlib import Path

import requests

from src.data_extraction.data_extraction_config import (
    SKIP_EXISTING_DOWNLOADS,
    VICTORY_BASE_URL,
    VICTORY_CHAIN_ID,
    VICTORY_RAW_DATA_DIR,
)


def list_price_full_files() -> list[dict]:
    """Return all PriceFull file entries from the Victory API."""
    response = requests.get(
        f"{VICTORY_BASE_URL}/webapi/api/getfiles",
        params={"edi": VICTORY_CHAIN_ID},
        timeout=60,
    )
    response.raise_for_status()

    files = response.json()

    price_full_files = []
    for entry in files:
        file_type = str(entry.get("fileType", "")).lower()
        if file_type == "pricefull":
            price_full_files.append(entry)

    return price_full_files


def _select_latest_daily_snapshots(price_full_files: list[dict]) -> list[dict]:
    """Keep the latest PriceFull file per store for the latest available date."""

    # Step 1: Build a simple list with store, date, time, and original API entry.
    # Victory fileDate looks like: "2026-08-13 05:10:22"
    parsed_files = []
    for entry in price_full_files:
        file_date = entry.get("fileDate") or ""
        if " " not in file_date:
            continue

        date_text, time_text = file_date.split(" ", 1)
        parsed_files.append(
            {
                "store_id": entry.get("branchNumber"),
                "date": date_text,
                "time": time_text,
                "file_date": file_date,
                "filename": entry.get("fileName"),
                "entry": entry,
            }
        )

    if not parsed_files:
        return []

    # Step 2: Find the latest date available across all PriceFull files.
    latest_date = parsed_files[0]["date"]
    for file_info in parsed_files:
        if file_info["date"] > latest_date:
            latest_date = file_info["date"]

    # Step 3: Keep only files from that latest date.
    same_day_files = []
    for file_info in parsed_files:
        if file_info["date"] == latest_date:
            same_day_files.append(file_info)

    # Step 4: For each store, keep the file with the latest time.
    latest_file_by_store = {}
    for file_info in same_day_files:
        store_id = file_info["store_id"]
        time_text = file_info["time"]

        if store_id not in latest_file_by_store:
            latest_file_by_store[store_id] = file_info
            continue

        current_best_time = latest_file_by_store[store_id]["time"]
        if time_text > current_best_time:
            latest_file_by_store[store_id] = file_info

    selected_entries = []
    for store_id in sorted(latest_file_by_store):
        selected_entries.append(latest_file_by_store[store_id]["entry"])

    print(
        f"Latest date {latest_date}: selected {len(selected_entries)} store snapshot(s).",
        flush=True,
    )
    return selected_entries


def download_price_full_files(
    *,
    max_files: int | None = 3,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    """Download PriceFull `.gz` files into ``data/raw/victory``.

    Selects the latest snapshot per store for the latest available date.
    ``max_files`` limits how many stores are downloaded (development use).
    """
    output_dir = VICTORY_RAW_DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    price_full_files = list_price_full_files()
    selected_files = _select_latest_daily_snapshots(price_full_files)

    if max_files is not None:
        selected_files = selected_files[:max_files]

    print(f"Found {len(selected_files)} PriceFull file(s) to download.", flush=True)

    downloaded_files: list[Path] = []

    for entry in selected_files:
        remote_name = entry["fileName"]
        output_path = output_dir / remote_name

        if skip_existing and output_path.exists():
            print(f"Skipping existing file: {output_path.name}", flush=True)
            downloaded_files.append(output_path)
            continue

        download_url = f"{VICTORY_BASE_URL}/webapi/{VICTORY_CHAIN_ID}/{remote_name}"
        print(f"Downloading {remote_name}...", flush=True)

        with requests.get(download_url, timeout=120, stream=True) as response:
            response.raise_for_status()
            with output_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)

        downloaded_files.append(output_path)

    return downloaded_files
