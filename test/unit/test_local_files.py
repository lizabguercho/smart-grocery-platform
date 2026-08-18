from pathlib import Path

import pytest

from src.data_extraction.local_files import (
    list_local_promo_full_files,
    list_local_stores_files,
    require_local_files,
)


def test_list_local_stores_files_matches_stores_glob(tmp_path: Path) -> None:
    stores_file = tmp_path / "Stores7290027600007-000-000-20260722-030000.gz"
    price_file = tmp_path / "PriceFull7290027600007-001-001-20260722-030000.gz"
    stores_file.write_bytes(b"stores")
    price_file.write_bytes(b"prices")

    assert list_local_stores_files(tmp_path) == [stores_file]


def test_list_local_promo_full_files_matches_promo_full_glob(tmp_path: Path) -> None:
    promo_file = tmp_path / "PromoFull7290027600007-001-001-20260816-030000.gz"
    price_file = tmp_path / "PriceFull7290027600007-001-001-20260722-030000.gz"
    promo_file.write_bytes(b"promo")
    price_file.write_bytes(b"prices")

    assert list_local_promo_full_files(tmp_path) == [promo_file]


def test_require_local_files_uses_custom_file_label(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No Stores files"):
        require_local_files([], tmp_path, file_label="Stores")
