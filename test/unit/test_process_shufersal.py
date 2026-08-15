from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Self
from unittest.mock import MagicMock, patch

import pytest

from src.data_extraction.data_extraction_config import (
    SHUFERSAL_CATEGORY_URL,
    SHUFERSAL_CHAIN_NAME,
    ShufersalPriceCategory,
)
from src.data_extraction.models import PriceFullProduct
from src.data_extraction.process_shufersal import (
    _select_latest_daily_snapshots,
    download_files,
    extract_download_prices_full_links,
    get_all_price_full_links,
    get_page,
    main,
)

STORE_001_LATEST = (
    "https://example.com/PriceFull7290027600007-001-001-20260722-030000.gz"
)
STORE_001_EARLIER = (
    "https://example.com/PriceFull7290027600007-001-001-20260722-010000.gz"
)
STORE_001_PREVIOUS_DAY = (
    "https://example.com/PriceFull7290027600007-001-001-20260721-230000.gz"
)
STORE_002 = "https://example.com/PriceFull7290027600007-001-002-20260722-040000.gz"


def _html_with_links(*hrefs: str) -> str:
    anchors = "".join(f'<a href="{href}">download</a>' for href in hrefs)
    return f"<html><body>{anchors}</body></html>"


PIPELINE_PATCHES = (
    "get_all_price_full_links",
    "download_files",
    "parse_price_full_files",
    "utils.save_to_csv",
    "load_products_to_staging",
    "validate_staging",
    "load_products",
    "load_product_prices",
    "validate_product_prices",
    "clear_staging",
)


@contextmanager
def _patch_pipeline(**mocks: MagicMock) -> Iterator[dict[str, MagicMock]]:
    patched: dict[str, MagicMock] = {}
    with ExitStack() as stack:
        for name in PIPELINE_PATCHES:
            mock = mocks.get(name, MagicMock())
            patched[name] = stack.enter_context(
                patch(f"src.data_extraction.process_shufersal.{name}", mock)
            )
        yield patched


class _FakeDownloadResponse:
    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 8192):
        yield b"price-full"

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def test_extract_download_prices_full_links_keeps_only_pricefull_hrefs() -> None:
    html = _html_with_links(
        STORE_001_LATEST,
        "https://example.com/PromoFull7290027600007-001-001-20260722-030000.gz",
        "/FileObject/PriceFull7290027600007-001-003-20260722-050000.gz",
    )

    links = extract_download_prices_full_links(html)

    assert STORE_001_LATEST in links
    assert all("pricefull" in link.lower() for link in links)
    assert any(link.endswith("001-003-20260722-050000.gz") for link in links)


def test_get_page_passes_category_store_and_page() -> None:
    response = MagicMock()
    response.text = "<html/>"

    with patch(
        "src.data_extraction.process_shufersal.requests.get",
        return_value=response,
    ) as get:
        html = get_page(page=2)

    assert html == "<html/>"
    get.assert_called_once_with(
        SHUFERSAL_CATEGORY_URL,
        params={
            "catID": ShufersalPriceCategory.PRICES_FULL.value,
            "storeId": 0,
            "page": 2,
        },
        timeout=30,
    )


def test_get_all_price_full_links_stops_when_filenames_repeat() -> None:
    first_page = _html_with_links(f"{STORE_001_LATEST}?sig=aaa")
    repeated_page = _html_with_links(f"{STORE_001_LATEST}?sig=bbb")

    with patch(
        "src.data_extraction.process_shufersal.get_page",
        side_effect=[first_page, repeated_page],
    ) as get_page_mock:
        links = get_all_price_full_links()

    assert get_page_mock.call_count == 2
    assert len(links) == 1
    assert "PriceFull7290027600007-001-001-20260722-030000.gz" in links[0]


def test_get_all_price_full_links_respects_max_pages() -> None:
    html = _html_with_links(STORE_001_LATEST, STORE_002)

    with patch(
        "src.data_extraction.process_shufersal.get_page",
        return_value=html,
    ) as get_page_mock:
        links = get_all_price_full_links(max_pages=1)

    assert get_page_mock.call_count == 1
    get_page_mock.assert_called_with(page=1)
    assert len(links) == 2


def test_select_latest_daily_snapshots_keeps_latest_time_per_store() -> None:
    selected = _select_latest_daily_snapshots(
        [
            STORE_001_PREVIOUS_DAY,
            STORE_001_EARLIER,
            STORE_001_LATEST,
            STORE_002,
        ]
    )

    assert selected == [STORE_001_LATEST, STORE_002]


def test_download_files_applies_max_files_after_snapshot_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.data_extraction.process_shufersal.RAW_DATA_DIR",
        tmp_path,
    )

    with patch(
        "src.data_extraction.process_shufersal.requests.get",
        return_value=_FakeDownloadResponse(),
    ) as get:
        files = download_files(
            [STORE_001_LATEST, STORE_002],
            max_files=1,
            skip_existing=False,
        )

    assert len(files) == 1
    assert files[0].name == Path(STORE_001_LATEST).name
    assert get.call_count == 1


def test_download_files_skips_existing_snapshots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.data_extraction.process_shufersal.RAW_DATA_DIR",
        tmp_path,
    )
    existing = tmp_path / Path(STORE_001_LATEST).name
    existing.write_bytes(b"already downloaded")

    with patch("src.data_extraction.process_shufersal.requests.get") as get:
        files = download_files([STORE_001_LATEST], skip_existing=True)

    assert files == [existing]
    get.assert_not_called()


def test_main_parses_downloaded_files_then_loads_and_validates(
    product: PriceFullProduct,
) -> None:
    downloaded_files = [Path("PriceFull7290027600007-001-001-20260722-030000.gz")]
    order: list[str] = []

    def track(name: str, return_value: object = None):
        def _side_effect(*args: object, **kwargs: object) -> object:
            order.append(name)
            return return_value

        return _side_effect

    mocks = {
        "get_all_price_full_links": MagicMock(
            side_effect=track("get_all_price_full_links", [STORE_001_LATEST])
        ),
        "download_files": MagicMock(
            side_effect=track("download_files", downloaded_files)
        ),
        "parse_price_full_files": MagicMock(
            side_effect=track("parse_price_full_files", [product])
        ),
        "utils.save_to_csv": MagicMock(side_effect=track("save_to_csv")),
        "load_products_to_staging": MagicMock(
            side_effect=track("load_products_to_staging")
        ),
        "validate_staging": MagicMock(side_effect=track("validate_staging")),
        "load_products": MagicMock(side_effect=track("load_products")),
        "load_product_prices": MagicMock(side_effect=track("load_product_prices")),
        "validate_product_prices": MagicMock(
            side_effect=track("validate_product_prices")
        ),
        "clear_staging": MagicMock(side_effect=track("clear_staging")),
    }

    with _patch_pipeline(**mocks):
        main(download=True, max_files=3, max_pages=2)

    mocks["get_all_price_full_links"].assert_called_once_with(max_pages=2)
    mocks["download_files"].assert_called_once_with([STORE_001_LATEST], max_files=3)
    mocks["parse_price_full_files"].assert_called_once_with(downloaded_files)
    mocks["utils.save_to_csv"].assert_called_once_with([product], SHUFERSAL_CHAIN_NAME)
    mocks["load_products_to_staging"].assert_called_once_with([product])
    assert order == [
        "get_all_price_full_links",
        "download_files",
        "parse_price_full_files",
        "save_to_csv",
        "load_products_to_staging",
        "validate_staging",
        "load_products",
        "load_product_prices",
        "validate_product_prices",
        "clear_staging",
    ]


def test_main_uses_local_files_when_download_is_disabled(
    tmp_path: Path,
    product: PriceFullProduct,
) -> None:
    local_file = tmp_path / "PriceFull7290027600007-001-001-20260722-030000.gz"
    local_file.write_bytes(b"unused")

    get_links = MagicMock()
    parse = MagicMock(return_value=[product])
    load_staging = MagicMock()

    with (
        patch("src.data_extraction.process_shufersal.RAW_DATA_DIR", tmp_path),
        _patch_pipeline(
            get_all_price_full_links=get_links,
            parse_price_full_files=parse,
            load_products_to_staging=load_staging,
        ),
    ):
        main(download=False)

    get_links.assert_not_called()
    parse.assert_called_once_with([local_file])
    load_staging.assert_called_once_with([product])


def test_main_raises_when_local_files_are_missing(tmp_path: Path) -> None:
    with (
        patch("src.data_extraction.process_shufersal.RAW_DATA_DIR", tmp_path),
        pytest.raises(FileNotFoundError, match="No PriceFull files"),
    ):
        main(download=False)
