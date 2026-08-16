from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.data_extraction.shufersal.extractor import ShufersalExtractor
from src.etl.constants import STORES_NOT_IMPLEMENTED_MESSAGE
from src.etl.enums import ExtractType
from src.etl.options import PipelineOptions

EXTRACTOR_MODULE = "src.data_extraction.shufersal.extractor"
STORE_001_LATEST = (
    "https://example.com/PriceFull7290027600007-001-001-20260722-030000.gz"
)


def test_shufersal_extractor_downloads_with_max_pages_and_max_files() -> None:
    downloaded_files = [Path("PriceFull7290027600007-001-001-20260722-030000.gz")]
    extractor = ShufersalExtractor(
        ExtractType.PRICES_FULL,
        PipelineOptions(download=True, max_files=3, max_pages=2),
    )

    with (
        patch(
            f"{EXTRACTOR_MODULE}.get_all_price_full_links",
            return_value=[STORE_001_LATEST],
        ) as get_links,
        patch(
            f"{EXTRACTOR_MODULE}.download_files",
            return_value=downloaded_files,
        ) as download,
    ):
        files = extractor.extract()

    get_links.assert_called_once_with(max_pages=2)
    download.assert_called_once_with([STORE_001_LATEST], max_files=3)
    assert files == downloaded_files


def test_shufersal_extractor_uses_local_files_when_download_is_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_file = tmp_path / "PriceFull7290027600007-001-001-20260722-030000.gz"
    local_file.write_bytes(b"unused")
    monkeypatch.setattr(f"{EXTRACTOR_MODULE}.RAW_DATA_DIR", tmp_path)
    extractor = ShufersalExtractor(
        ExtractType.PRICES_FULL,
        PipelineOptions(download=False),
    )

    get_links = MagicMock()
    with patch(f"{EXTRACTOR_MODULE}.get_all_price_full_links", get_links):
        files = extractor.extract()

    get_links.assert_not_called()
    assert files == [local_file]


def test_shufersal_extractor_raises_when_local_files_are_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(f"{EXTRACTOR_MODULE}.RAW_DATA_DIR", tmp_path)
    extractor = ShufersalExtractor(
        ExtractType.PRICES_FULL,
        PipelineOptions(download=False),
    )

    with pytest.raises(FileNotFoundError, match="No PriceFull files"):
        extractor.extract()


def test_shufersal_extractor_stores_raises_not_implemented() -> None:
    extractor = ShufersalExtractor(ExtractType.STORES, PipelineOptions())

    with pytest.raises(NotImplementedError, match=STORES_NOT_IMPLEMENTED_MESSAGE):
        extractor.extract()
