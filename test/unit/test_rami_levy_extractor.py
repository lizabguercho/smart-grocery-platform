from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.data_extraction.rami_levy.download import (
    download_price_full_files,
    download_store_files,
    select_latest_daily_promo_full_snapshot_names,
    select_latest_daily_store_snapshot_names,
)
from src.data_extraction.rami_levy.extractor import RamiLevyExtractor
from src.etl.enums import ExtractType
from src.etl.options import PipelineOptions

DOWNLOAD_MODULE = "src.data_extraction.rami_levy.download"
EXTRACTOR_MODULE = "src.data_extraction.rami_levy.extractor"
STORES_LATEST = "Stores7290058140886-000-20260816-050500.xml"
STORES_EARLIER = "Stores7290058140886-000-20260816-040500.xml"
PRICE_FULL_NAME = "PriceFull7290058140886-001-001-20260816-030000.gz"
PROMO_001_LATEST = "PromoFull7290058140886-001-001-20260816-030000.gz"
PROMO_001_EARLIER = "PromoFull7290058140886-001-001-20260816-010000.gz"
PROMO_039 = "PromoFull7290058140886-001-039-20260816-040000.gz"
PROMO_039_NEWER_DATE = "PromoFull7290058140886-001-039-20260817-010000.gz"


def test_select_latest_daily_store_snapshot_names_ignores_price_full() -> None:
    selected = select_latest_daily_store_snapshot_names(
        [PRICE_FULL_NAME, STORES_EARLIER, STORES_LATEST]
    )

    assert selected == [STORES_LATEST]


def test_download_price_full_files_writes_to_rami_levy_price_full_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        f"{DOWNLOAD_MODULE}.RAMI_LEVY_PRICE_FULL_RAW_DATA_DIR", tmp_path
    )
    ftp = MagicMock()
    ftp.retrlines.side_effect = lambda _command, callback: callback(PRICE_FULL_NAME)

    def retrbinary(_command: str, writer) -> None:
        writer(b"price-full")

    ftp.retrbinary.side_effect = retrbinary

    with patch(f"{DOWNLOAD_MODULE}._connect", return_value=ftp):
        files = download_price_full_files(max_files=3, skip_existing=False)

    assert files == [tmp_path / PRICE_FULL_NAME]
    assert (tmp_path / PRICE_FULL_NAME).read_bytes() == b"price-full"
    ftp.retrbinary.assert_called_once()


def test_rami_levy_extractor_price_full_uses_local_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_file = tmp_path / PRICE_FULL_NAME
    local_file.write_bytes(b"unused")
    monkeypatch.setattr(
        f"{EXTRACTOR_MODULE}.RAMI_LEVY_PRICE_FULL_RAW_DATA_DIR", tmp_path
    )
    extractor = RamiLevyExtractor(
        ExtractType.PRICES_FULL,
        PipelineOptions(download=False),
    )

    download = MagicMock()
    with patch(f"{EXTRACTOR_MODULE}.download_price_full_files", download):
        files = extractor.extract()

    download.assert_not_called()
    assert files == [local_file]


def test_download_store_files_writes_to_rami_levy_stores_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(f"{DOWNLOAD_MODULE}.RAMI_LEVY_STORES_RAW_DATA_DIR", tmp_path)
    ftp = MagicMock()
    ftp.retrlines.side_effect = lambda _command, callback: callback(STORES_LATEST)

    def retrbinary(_command: str, writer) -> None:
        writer(b"stores-xml")

    ftp.retrbinary.side_effect = retrbinary

    with patch(f"{DOWNLOAD_MODULE}._connect", return_value=ftp):
        files = download_store_files(max_files=3, skip_existing=False)

    assert files == [tmp_path / STORES_LATEST]
    assert (tmp_path / STORES_LATEST).read_bytes() == b"stores-xml"
    ftp.retrbinary.assert_called_once()


def test_rami_levy_extractor_stores_downloads() -> None:
    downloaded_files = [Path("data/raw/stores/rami_levy") / STORES_LATEST]
    extractor = RamiLevyExtractor(
        ExtractType.STORES,
        PipelineOptions(download=True, max_files=3),
    )

    with patch(
        f"{EXTRACTOR_MODULE}.download_store_files",
        return_value=downloaded_files,
    ) as download:
        files = extractor.extract()

    download.assert_called_once_with(max_files=3)
    assert files == downloaded_files


def test_rami_levy_extractor_stores_uses_local_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_file = tmp_path / STORES_LATEST
    local_file.write_bytes(b"unused")
    monkeypatch.setattr(f"{EXTRACTOR_MODULE}.RAMI_LEVY_STORES_RAW_DATA_DIR", tmp_path)
    extractor = RamiLevyExtractor(
        ExtractType.STORES,
        PipelineOptions(download=False),
    )

    download = MagicMock()
    with patch(f"{EXTRACTOR_MODULE}.download_store_files", download):
        files = extractor.extract()

    download.assert_not_called()
    assert files == [local_file]


def test_select_latest_daily_promo_full_snapshot_names_skips_store_039() -> None:
    selected = select_latest_daily_promo_full_snapshot_names(
        [
            PRICE_FULL_NAME,
            PROMO_001_EARLIER,
            PROMO_001_LATEST,
            PROMO_039,
            PROMO_039_NEWER_DATE,
        ]
    )

    assert selected == [PROMO_001_LATEST]


def test_rami_levy_extractor_promo_full_downloads() -> None:
    downloaded_files = [Path("data/raw/promo_full/rami_levy") / PROMO_001_LATEST]
    extractor = RamiLevyExtractor(
        ExtractType.PROMO_FULL,
        PipelineOptions(download=True, max_files=3),
    )

    with patch(
        f"{EXTRACTOR_MODULE}.download_promo_full_files",
        return_value=downloaded_files,
    ) as download:
        files = extractor.extract()

    download.assert_called_once_with(max_files=3)
    assert files == downloaded_files


def test_rami_levy_extractor_promo_full_uses_local_files_and_skips_039(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_file = tmp_path / PROMO_001_LATEST
    skipped = tmp_path / PROMO_039
    local_file.write_bytes(b"unused")
    skipped.write_bytes(b"unsupported")
    monkeypatch.setattr(
        f"{EXTRACTOR_MODULE}.RAMI_LEVY_PROMO_FULL_RAW_DATA_DIR",
        tmp_path,
    )
    extractor = RamiLevyExtractor(
        ExtractType.PROMO_FULL,
        PipelineOptions(download=False),
    )

    download = MagicMock()
    with patch(f"{EXTRACTOR_MODULE}.download_promo_full_files", download):
        files = extractor.extract()

    download.assert_not_called()
    assert files == [local_file]
