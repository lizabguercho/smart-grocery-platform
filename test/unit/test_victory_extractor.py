from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.data_extraction.victory.download import (
    download_price_full_files,
    download_store_files,
    list_promo_full_files,
    list_store_files,
    select_latest_daily_snapshot_entries,
)
from src.data_extraction.victory.extractor import VictoryExtractor
from src.etl.enums import ExtractType
from src.etl.options import PipelineOptions

DOWNLOAD_MODULE = "src.data_extraction.victory.download"
EXTRACTOR_MODULE = "src.data_extraction.victory.extractor"
STORES_LATEST = "Stores7290696200003-000-20260816060100-060100.gz"
STORES_EARLIER = "Stores7290696200003-000-20260815050100-050100.gz"
PRICE_FULL_NAME = "PriceFull7290696200003-001-20260816-030000.gz"
PROMO_LATEST = "PromoFull7290696200003-001-001-20260816-030000.gz"
PROMO_EARLIER = "PromoFull7290696200003-001-001-20260816-010000.gz"


def _entry(
    *,
    file_type: str,
    file_name: str,
    file_date: str,
    branch_number: int,
) -> dict:
    return {
        "fileType": file_type,
        "fileName": file_name,
        "fileDate": file_date,
        "branchNumber": branch_number,
    }


def test_select_latest_daily_snapshot_entries_keeps_latest_stores_file() -> None:
    selected = select_latest_daily_snapshot_entries(
        [
            _entry(
                file_type="stores",
                file_name=STORES_EARLIER,
                file_date="2026-08-15 05:01:00",
                branch_number=0,
            ),
            _entry(
                file_type="stores",
                file_name=STORES_LATEST,
                file_date="2026-08-16 06:01:00",
                branch_number=0,
            ),
        ]
    )

    assert [entry["fileName"] for entry in selected] == [STORES_LATEST]


def test_list_store_files_filters_out_price_full() -> None:
    response = MagicMock()
    response.json.return_value = [
        _entry(
            file_type="pricefull",
            file_name=PRICE_FULL_NAME,
            file_date="2026-08-16 03:00:00",
            branch_number=1,
        ),
        _entry(
            file_type="stores",
            file_name=STORES_LATEST,
            file_date="2026-08-16 06:01:00",
            branch_number=0,
        ),
    ]

    with patch(f"{DOWNLOAD_MODULE}.requests.get", return_value=response):
        files = list_store_files()

    assert [entry["fileName"] for entry in files] == [STORES_LATEST]


def test_download_price_full_files_writes_to_victory_price_full_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(f"{DOWNLOAD_MODULE}.VICTORY_PRICE_FULL_RAW_DATA_DIR", tmp_path)

    list_response = MagicMock()
    list_response.json.return_value = [
        _entry(
            file_type="pricefull",
            file_name=PRICE_FULL_NAME,
            file_date="2026-08-16 03:00:00",
            branch_number=1,
        ),
        _entry(
            file_type="stores",
            file_name=STORES_LATEST,
            file_date="2026-08-16 06:01:00",
            branch_number=0,
        ),
    ]

    download_response = MagicMock()
    download_response.iter_content.return_value = [b"gzip-bytes"]
    download_response.__enter__.return_value = download_response
    download_response.__exit__.return_value = False

    def get(_url: str, *args, **kwargs):
        if kwargs.get("stream"):
            return download_response
        return list_response

    with patch(f"{DOWNLOAD_MODULE}.requests.get", side_effect=get):
        files = download_price_full_files(max_files=3, skip_existing=False)

    assert files == [tmp_path / PRICE_FULL_NAME]
    assert (tmp_path / PRICE_FULL_NAME).read_bytes() == b"gzip-bytes"


def test_victory_extractor_price_full_uses_local_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_file = tmp_path / PRICE_FULL_NAME
    local_file.write_bytes(b"unused")
    monkeypatch.setattr(f"{EXTRACTOR_MODULE}.VICTORY_PRICE_FULL_RAW_DATA_DIR", tmp_path)
    extractor = VictoryExtractor(
        ExtractType.PRICES_FULL,
        PipelineOptions(download=False),
    )

    download = MagicMock()
    with patch(f"{EXTRACTOR_MODULE}.download_price_full_files", download):
        files = extractor.extract()

    download.assert_not_called()
    assert files == [local_file]


def test_download_store_files_writes_to_victory_stores_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(f"{DOWNLOAD_MODULE}.VICTORY_STORES_RAW_DATA_DIR", tmp_path)

    list_response = MagicMock()
    list_response.json.return_value = [
        _entry(
            file_type="pricefull",
            file_name=PRICE_FULL_NAME,
            file_date="2026-08-16 03:00:00",
            branch_number=1,
        ),
        _entry(
            file_type="stores",
            file_name=STORES_LATEST,
            file_date="2026-08-16 06:01:00",
            branch_number=0,
        ),
    ]

    download_response = MagicMock()
    download_response.iter_content.return_value = [b"gzip-bytes"]
    download_response.__enter__.return_value = download_response
    download_response.__exit__.return_value = False

    def get(_url: str, *args, **kwargs):
        if kwargs.get("stream"):
            return download_response
        return list_response

    with patch(f"{DOWNLOAD_MODULE}.requests.get", side_effect=get):
        files = download_store_files(max_files=3, skip_existing=False)

    assert files == [tmp_path / STORES_LATEST]
    assert (tmp_path / STORES_LATEST).read_bytes() == b"gzip-bytes"


def test_victory_extractor_stores_downloads() -> None:
    downloaded_files = [Path("data/raw/stores/victory") / STORES_LATEST]
    extractor = VictoryExtractor(
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


def test_victory_extractor_stores_uses_local_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_file = tmp_path / STORES_LATEST
    local_file.write_bytes(b"unused")
    monkeypatch.setattr(f"{EXTRACTOR_MODULE}.VICTORY_STORES_RAW_DATA_DIR", tmp_path)
    extractor = VictoryExtractor(
        ExtractType.STORES,
        PipelineOptions(download=False),
    )

    download = MagicMock()
    with patch(f"{EXTRACTOR_MODULE}.download_store_files", download):
        files = extractor.extract()

    download.assert_not_called()
    assert files == [local_file]


def test_list_promo_full_files_filters_out_price_full_and_stores() -> None:
    response = MagicMock()
    response.json.return_value = [
        _entry(
            file_type="pricefull",
            file_name=PRICE_FULL_NAME,
            file_date="2026-08-16 03:00:00",
            branch_number=1,
        ),
        _entry(
            file_type="stores",
            file_name=STORES_LATEST,
            file_date="2026-08-16 06:01:00",
            branch_number=0,
        ),
        _entry(
            file_type="promofull",
            file_name=PROMO_LATEST,
            file_date="2026-08-16 03:00:00",
            branch_number=1,
        ),
    ]

    with patch(f"{DOWNLOAD_MODULE}.requests.get", return_value=response):
        files = list_promo_full_files()

    assert [entry["fileName"] for entry in files] == [PROMO_LATEST]


def test_select_latest_daily_snapshot_entries_keeps_latest_promo_full_file() -> None:
    selected = select_latest_daily_snapshot_entries(
        [
            _entry(
                file_type="promofull",
                file_name=PROMO_EARLIER,
                file_date="2026-08-16 01:00:00",
                branch_number=1,
            ),
            _entry(
                file_type="promofull",
                file_name=PROMO_LATEST,
                file_date="2026-08-16 03:00:00",
                branch_number=1,
            ),
        ]
    )

    assert [entry["fileName"] for entry in selected] == [PROMO_LATEST]


def test_victory_extractor_promo_full_downloads() -> None:
    downloaded_files = [Path("data/raw/promo_full/victory") / PROMO_LATEST]
    extractor = VictoryExtractor(
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


def test_victory_extractor_promo_full_uses_local_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_file = tmp_path / PROMO_LATEST
    local_file.write_bytes(b"unused")
    monkeypatch.setattr(
        f"{EXTRACTOR_MODULE}.VICTORY_PROMO_FULL_RAW_DATA_DIR",
        tmp_path,
    )
    extractor = VictoryExtractor(
        ExtractType.PROMO_FULL,
        PipelineOptions(download=False),
    )

    download = MagicMock()
    with patch(f"{EXTRACTOR_MODULE}.download_promo_full_files", download):
        files = extractor.extract()

    download.assert_not_called()
    assert files == [local_file]
