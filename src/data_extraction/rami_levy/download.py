"""Rami Levy PriceFull, Stores, and PromoFull file downloader via Cerberus FTP."""

from __future__ import annotations

from collections.abc import Callable
from ftplib import FTP
from pathlib import Path

from src.data_extraction.data_extraction_config import (
    PRICE_FULL_FILE_LABEL,
    PROMO_FULL_FILE_LABEL,
    RAMI_LEVY_FTP_HOST,
    RAMI_LEVY_FTP_PASSWORD,
    RAMI_LEVY_FTP_PORT,
    RAMI_LEVY_FTP_TIMEOUT_SECONDS,
    RAMI_LEVY_FTP_USERNAME,
    RAMI_LEVY_PRICE_FULL_RAW_DATA_DIR,
    RAMI_LEVY_PROMO_FULL_RAW_DATA_DIR,
    RAMI_LEVY_STORES_RAW_DATA_DIR,
    SKIP_EXISTING_DOWNLOADS,
    STORES_FILE_LABEL,
)
from src.data_extraction.snapshots import (
    DailySnapshot,
    is_unsupported_rami_levy_store_id,
    parse_price_full_filename,
    parse_promo_full_filename,
    parse_stores_filename,
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


def _snapshots_from_names(
    remote_names: list[str],
    parse_filename: Callable[[str], tuple[str, str, str] | None],
) -> list[DailySnapshot[str]]:
    snapshots: list[DailySnapshot[str]] = []
    for name in remote_names:
        fields = parse_filename(name)
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
    selected = select_latest_daily_snapshots(
        _snapshots_from_names(remote_names, parse_price_full_filename)
    )
    return [snapshot.payload for snapshot in selected]


def select_latest_daily_store_snapshot_names(remote_names: list[str]) -> list[str]:
    """Keep the latest Stores file per store for the latest available date."""
    selected = select_latest_daily_snapshots(
        _snapshots_from_names(remote_names, parse_stores_filename)
    )
    return [snapshot.payload for snapshot in selected]


def select_latest_daily_promo_full_snapshot_names(remote_names: list[str]) -> list[str]:
    """Keep the latest PromoFull file per store for the latest available date.

    Store 039 is skipped before date selection so its incompatible files
    cannot become the latest date.
    """
    snapshots = [
        snapshot
        for snapshot in _snapshots_from_names(remote_names, parse_promo_full_filename)
        if not is_unsupported_rami_levy_store_id(snapshot.store_id)
    ]
    selected = select_latest_daily_snapshots(snapshots)
    return [snapshot.payload for snapshot in selected]


def _download_selected_files(
    *,
    output_dir: Path,
    select_names: Callable[[list[str]], list[str]],
    file_label: str,
    max_files: int | None,
    skip_existing: bool,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    ftp = _connect()

    try:
        remote_names: list[str] = []
        ftp.retrlines("NLST", remote_names.append)

        selected_files = select_names(remote_names)
        if max_files is not None:
            selected_files = selected_files[:max_files]

        print(
            f"Found {len(selected_files)} {file_label} file(s) to download.",
            flush=True,
        )

        downloaded_files: list[Path] = []

        for remote_name in selected_files:
            output_path = output_dir / Path(remote_name).name

            if skip_existing and output_path.exists():
                print(f"Skipping existing file: {output_path.name}", flush=True)
                downloaded_files.append(output_path)
                continue

            print(f"Downloading {output_path.name}...", flush=True)
            with output_path.open("wb") as file:
                ftp.retrbinary(f"RETR {remote_name}", file.write)

            downloaded_files.append(output_path)

        return downloaded_files
    finally:
        ftp.quit()


def download_price_full_files(
    *,
    max_files: int | None = DEFAULT_MAX_FILES,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    """Download PriceFull `.gz` files into ``data/raw/price_full/rami_levy``."""
    return _download_selected_files(
        output_dir=RAMI_LEVY_PRICE_FULL_RAW_DATA_DIR,
        select_names=select_latest_daily_snapshot_names,
        file_label=PRICE_FULL_FILE_LABEL,
        max_files=max_files,
        skip_existing=skip_existing,
    )


def download_store_files(
    *,
    max_files: int | None = DEFAULT_MAX_FILES,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    """Download Stores `.gz` files into ``data/raw/stores/rami_levy``."""
    return _download_selected_files(
        output_dir=RAMI_LEVY_STORES_RAW_DATA_DIR,
        select_names=select_latest_daily_store_snapshot_names,
        file_label=STORES_FILE_LABEL,
        max_files=max_files,
        skip_existing=skip_existing,
    )


def download_promo_full_files(
    *,
    max_files: int | None = DEFAULT_MAX_FILES,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    """Download PromoFull `.gz` files into ``data/raw/promo_full/rami_levy``."""
    return _download_selected_files(
        output_dir=RAMI_LEVY_PROMO_FULL_RAW_DATA_DIR,
        select_names=select_latest_daily_promo_full_snapshot_names,
        file_label=PROMO_FULL_FILE_LABEL,
        max_files=max_files,
        skip_existing=skip_existing,
    )
