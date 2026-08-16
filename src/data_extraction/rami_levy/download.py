"""Rami Levy PriceFull file downloader via Cerberus FTP."""

from __future__ import annotations

from ftplib import FTP
from pathlib import Path

from src.data_extraction.data_extraction_config import (
    RAMI_LEVY_FTP_HOST,
    RAMI_LEVY_FTP_PASSWORD,
    RAMI_LEVY_FTP_PORT,
    RAMI_LEVY_FTP_TIMEOUT_SECONDS,
    RAMI_LEVY_FTP_USERNAME,
    RAMI_LEVY_RAW_DATA_DIR,
    SKIP_EXISTING_DOWNLOADS,
)
from src.data_extraction.snapshots import (
    DailySnapshot,
    parse_price_full_filename,
    select_latest_daily_snapshots,
)
from src.etl.constants import DEFAULT_MAX_FILES


def _connect() -> FTP:
    ftp = FTP()
    ftp.connect(
        RAMI_LEVY_FTP_HOST,
        RAMI_LEVY_FTP_PORT,
        timeout=RAMI_LEVY_FTP_TIMEOUT_SECONDS,
    )
    ftp.login(RAMI_LEVY_FTP_USERNAME, RAMI_LEVY_FTP_PASSWORD)
    ftp.set_pasv(False)  # active mode
    return ftp


def _snapshots_from_names(remote_names: list[str]) -> list[DailySnapshot[str]]:
    snapshots: list[DailySnapshot[str]] = []
    for name in remote_names:
        fields = parse_price_full_filename(name)
        if fields is None:
            continue

        store_id, date, time = fields
        snapshots.append(
            DailySnapshot(
                store_id=store_id,
                date=date,
                time=time,
                payload=name,
            )
        )
    return snapshots


def select_latest_daily_snapshot_names(remote_names: list[str]) -> list[str]:
    """Keep the latest PriceFull file per store for the latest available date."""
    selected = select_latest_daily_snapshots(_snapshots_from_names(remote_names))
    return [snapshot.payload for snapshot in selected]


def download_price_full_files(
    *,
    max_files: int | None = DEFAULT_MAX_FILES,
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

        price_full_files = select_latest_daily_snapshot_names(remote_names)
        if max_files is not None:
            price_full_files = price_full_files[:max_files]

        print(
            f"Found {len(price_full_files)} PriceFull file(s) to download.",
            flush=True,
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
