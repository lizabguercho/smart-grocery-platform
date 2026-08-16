from pathlib import Path

from src.data_extraction.data_extraction_config import (
    PRICE_FULL_FILE_GLOB,
    PRICE_FULL_FILE_LABEL,
)
from src.etl.constants import MISSING_LOCAL_FILES_MESSAGE


def list_local_price_full_files(raw_dir: Path) -> list[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    return sorted(raw_dir.glob(PRICE_FULL_FILE_GLOB))


def require_local_files(files: list[Path], raw_dir: Path) -> list[Path]:
    if not files:
        raise FileNotFoundError(
            MISSING_LOCAL_FILES_MESSAGE.format(
                file_label=PRICE_FULL_FILE_LABEL,
                raw_dir=raw_dir,
            )
        )
    return files
