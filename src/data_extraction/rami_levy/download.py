"""Rami Levy PriceFull file downloader via Cerberus FTP."""

from __future__ import annotations

from ftplib import FTP
from pathlib import Path

from src.data_extraction.data_extraction_config import (
    RAMI_LEVY_FTP_HOST,
    RAMI_LEVY_FTP_PASSWORD,
    RAMI_LEVY_FTP_TIMEOUT_SECONDS,
    RAMI_LEVY_FTP_USERNAME,
    RAMI_LEVY_RAW_DATA_DIR,
    SKIP_EXISTING_DOWNLOADS,
)


def _connect() -> FTP:
    ftp = FTP()
    ftp.connect(RAMI_LEVY_FTP_HOST, 21, timeout=RAMI_LEVY_FTP_TIMEOUT_SECONDS)
    ftp.login(RAMI_LEVY_FTP_USERNAME, RAMI_LEVY_FTP_PASSWORD)
    ftp.set_pasv(False)  # active mode
    return ftp


def _parse_price_full_filename(name: str) -> tuple[str, str, str] | None:
    """Return (store_id, date, time) from a PriceFull filename, or None."""
    # Expected: PriceFull{chain}-{sub}-{store}-{YYYYMMDD}-{HHMMSS}.gz
    if not name.lower().startswith("pricefull") or not name.lower().endswith(".gz"):
        return None

    stem = name[:-3]  # remove .gz
    parts = stem.split("-")
    if len(parts) < 5:
        return None

    store_id = parts[-3]
    date = parts[-2]
    time = parts[-1]
    return store_id, date, time


def _select_latest_daily_snapshots(remote_names: list[str]) -> list[str]:
    """Keep the latest PriceFull file per store for the latest available date."""

    # Step 1: Parse each PriceFull filename into store_id, date, and time.
    parsed_files = []
    for name in remote_names:
        fields = _parse_price_full_filename(name)
        if fields is None:
            continue

        store_id, date, time = fields
        parsed_files.append(
            {
                "store_id": store_id,
                "date": date,
                "time": time,
                "filename": name,
            }
        )

    if not parsed_files:
        return []

    # Step 2: Find the latest date available across all PriceFull files.
    latest_date = parsed_files[0]["date"]
    for file_info in parsed_files:
        latest_date = max(latest_date, file_info["date"])

    # Step 3: Keep only files from that latest date.
    same_day_files = []
    for file_info in parsed_files:
        if file_info["date"] == latest_date:
            same_day_files.append(file_info)

    # Step 4: For each store, keep the file with the latest time.
    latest_file_by_store = {}
    for file_info in same_day_files:
        store_id = file_info["store_id"]
        time = file_info["time"]

        if store_id not in latest_file_by_store:
            latest_file_by_store[store_id] = file_info
            continue

        current_best_time = latest_file_by_store[store_id]["time"]
        if time > current_best_time:
            latest_file_by_store[store_id] = file_info

    selected_filenames = []
    for store_id in sorted(latest_file_by_store):
        selected_filenames.append(latest_file_by_store[store_id]["filename"])

    print(
        f"Latest date {latest_date}: selected {len(selected_filenames)} store snapshot(s).",
        flush=True,
    )
    return selected_filenames


def download_price_full_files(
    *,
    max_files: int | None = 3,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    """Download PriceFull `.gz` files into ``data/raw/rami_levy``.

    Selects the latest snapshot per store for the latest available date.
    ``max_files`` limits how many stores are downloaded (development use).
    """
    output_dir = RAMI_LEVY_RAW_DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    ftp = _connect()

    try:
        remote_names: list[str] = []
        ftp.retrlines("NLST", remote_names.append)

        price_full_files = _select_latest_daily_snapshots(remote_names)
        if max_files is not None:
            price_full_files = price_full_files[:max_files]

        print(
            f"Found {len(price_full_files)} PriceFull file(s) to download.", flush=True
        )

        downloaded_files: list[Path] = []

        for remote_name in price_full_files:
            output_path = output_dir / remote_name

            if skip_existing and output_path.exists():
                print(f"Skipping existing file: {output_path.name}", flush=True)
                downloaded_files.append(output_path)
                continue

            print(f"Downloading {remote_name}...", flush=True)
            with output_path.open("wb") as file:
                ftp.retrbinary(f"RETR {remote_name}", file.write)

            downloaded_files.append(output_path)

        return downloaded_files
    finally:
        ftp.quit()
