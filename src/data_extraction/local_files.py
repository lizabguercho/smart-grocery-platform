from pathlib import Path

from src.data_extraction.data_extraction_config import (
    PRICE_FULL_FILE_GLOB,
    PRICE_FULL_FILE_LABEL,
    PROMO_FULL_FILE_GLOB,
    STORES_FILE_GLOB,
)
from src.etl.constants import MISSING_LOCAL_FILES_MESSAGE


def list_local_price_full_files(raw_dir: Path) -> list[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    return sorted(raw_dir.glob(PRICE_FULL_FILE_GLOB))


def list_local_stores_files(raw_dir: Path) -> list[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    return sorted(raw_dir.glob(STORES_FILE_GLOB))


def list_local_promo_full_files(raw_dir: Path) -> list[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    return sorted(raw_dir.glob(PROMO_FULL_FILE_GLOB))


def require_local_files(
    files: list[Path],
    raw_dir: Path,
    file_label: str = PRICE_FULL_FILE_LABEL,
) -> list[Path]:
    if not files:
        raise FileNotFoundError(
            MISSING_LOCAL_FILES_MESSAGE.format(
                file_label=file_label,
                raw_dir=raw_dir,
            )
        )
    return files
