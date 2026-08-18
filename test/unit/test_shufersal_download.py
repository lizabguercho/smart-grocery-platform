from __future__ import annotations

from pathlib import Path
from typing import Self
from unittest.mock import MagicMock, patch

import pytest

from src.data_extraction.data_extraction_config import (
    SHUFERSAL_CATEGORY_URL,
    SHUFERSAL_DEFAULT_STORE_ID,
    SHUFERSAL_DOWNLOAD_TIMEOUT_SECONDS,
    SHUFERSAL_PAGE_TIMEOUT_SECONDS,
    SHUFERSAL_PARAM_CATEGORY_ID,
    SHUFERSAL_PARAM_PAGE,
    SHUFERSAL_PARAM_STORE_ID,
    ShufersalPriceCategory,
)
from src.data_extraction.shufersal.download import (
    download_files,
    download_promo_full_files,
    download_store_files,
    extract_download_prices_full_links,
    extract_download_promo_full_links,
    extract_download_stores_links,
    get_all_price_full_links,
    get_all_promo_full_links,
    get_all_stores_links,
    get_page,
    select_latest_daily_promo_full_snapshot_links,
    select_latest_daily_snapshot_links,
    select_latest_daily_store_snapshot_links,
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
STORES_LATEST = "https://example.com/Stores7290027600007-000-000-20260722-030000.gz"
STORES_EARLIER = "https://example.com/Stores7290027600007-000-000-20260722-010000.gz"
PROMO_001_LATEST = (
    "https://example.com/PromoFull7290027600007-001-001-20260816-030000.gz"
)
PROMO_001_EARLIER = (
    "https://example.com/PromoFull7290027600007-001-001-20260816-010000.gz"
)
PROMO_002 = "https://example.com/PromoFull7290027600007-001-002-20260816-040000.gz"
DOWNLOAD_MODULE = "src.data_extraction.shufersal.download"


def _html_with_links(*hrefs: str) -> str:
    anchors = "".join(f'<a href="{href}">download</a>' for href in hrefs)
    return f"<html><body>{anchors}</body></html>"


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

    with patch(f"{DOWNLOAD_MODULE}.requests.get", return_value=response) as get:
        html = get_page(page=2)

    assert html == "<html/>"
    get.assert_called_once_with(
        SHUFERSAL_CATEGORY_URL,
        params={
            SHUFERSAL_PARAM_CATEGORY_ID: ShufersalPriceCategory.PRICES_FULL.value,
            SHUFERSAL_PARAM_STORE_ID: SHUFERSAL_DEFAULT_STORE_ID,
            SHUFERSAL_PARAM_PAGE: 2,
        },
        timeout=SHUFERSAL_PAGE_TIMEOUT_SECONDS,
    )


def test_get_all_price_full_links_stops_when_filenames_repeat() -> None:
    first_page = _html_with_links(f"{STORE_001_LATEST}?sig=aaa")
    repeated_page = _html_with_links(f"{STORE_001_LATEST}?sig=bbb")

    with patch(
        f"{DOWNLOAD_MODULE}.get_page",
        side_effect=[first_page, repeated_page],
    ) as get_page_mock:
        links = get_all_price_full_links()

    assert get_page_mock.call_count == 2
    assert len(links) == 1
    assert "PriceFull7290027600007-001-001-20260722-030000.gz" in links[0]


def test_get_all_price_full_links_respects_max_pages() -> None:
    html = _html_with_links(STORE_001_LATEST, STORE_002)

    with patch(
        f"{DOWNLOAD_MODULE}.get_page",
        return_value=html,
    ) as get_page_mock:
        links = get_all_price_full_links(max_pages=1)

    assert get_page_mock.call_count == 1
    get_page_mock.assert_called_with(page=1)
    assert len(links) == 2


def test_select_latest_daily_snapshot_links_keeps_latest_time_per_store() -> None:
    selected = select_latest_daily_snapshot_links(
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
        f"{DOWNLOAD_MODULE}.SHUFERSAL_PRICE_FULL_RAW_DATA_DIR", tmp_path
    )

    with patch(
        f"{DOWNLOAD_MODULE}.requests.get",
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
    get.assert_called_once()
    _, kwargs = get.call_args
    assert kwargs["timeout"] == SHUFERSAL_DOWNLOAD_TIMEOUT_SECONDS


def test_download_files_skips_existing_snapshots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        f"{DOWNLOAD_MODULE}.SHUFERSAL_PRICE_FULL_RAW_DATA_DIR", tmp_path
    )
    existing = tmp_path / Path(STORE_001_LATEST).name
    existing.write_bytes(b"already downloaded")

    with patch(f"{DOWNLOAD_MODULE}.requests.get") as get:
        files = download_files([STORE_001_LATEST], skip_existing=True)

    assert files == [existing]
    get.assert_not_called()


def test_extract_download_stores_links_keeps_only_stores_hrefs() -> None:
    html = _html_with_links(
        STORES_LATEST,
        STORE_001_LATEST,
        "/FileObject/Stores7290027600007-000-000-20260722-040000.gz",
    )

    links = extract_download_stores_links(html)

    assert STORES_LATEST in links
    assert all("stores" in link.lower() for link in links)
    assert any(link.endswith("000-000-20260722-040000.gz") for link in links)


def test_get_all_stores_links_requests_stores_category() -> None:
    html = _html_with_links(STORES_LATEST)

    with patch(
        f"{DOWNLOAD_MODULE}.get_page",
        return_value=html,
    ) as get_page_mock:
        links = get_all_stores_links(max_pages=1)

    get_page_mock.assert_called_once_with(
        category_id=ShufersalPriceCategory.STORES,
        page=1,
    )
    assert len(links) == 1


def test_select_latest_daily_store_snapshot_links_keeps_latest_time() -> None:
    selected = select_latest_daily_store_snapshot_links([STORES_EARLIER, STORES_LATEST])

    assert selected == [STORES_LATEST]


def test_download_store_files_writes_to_stores_raw_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(f"{DOWNLOAD_MODULE}.SHUFERSAL_STORES_RAW_DATA_DIR", tmp_path)

    with patch(
        f"{DOWNLOAD_MODULE}.requests.get",
        return_value=_FakeDownloadResponse(),
    ):
        files = download_store_files([STORES_LATEST], skip_existing=False)

    assert len(files) == 1
    assert files[0].parent == tmp_path
    assert files[0].name == Path(STORES_LATEST).name


def test_extract_download_promo_full_links_keeps_only_promofull_hrefs() -> None:
    html = _html_with_links(
        PROMO_001_LATEST,
        STORE_001_LATEST,
        "/FileObject/PromoFull7290027600007-001-003-20260816-050000.gz",
    )

    links = extract_download_promo_full_links(html)

    assert PROMO_001_LATEST in links
    assert all("promofull" in link.lower() for link in links)
    assert any(link.endswith("001-003-20260816-050000.gz") for link in links)


def test_get_all_promo_full_links_requests_promos_full_category() -> None:
    html = _html_with_links(PROMO_001_LATEST)

    with patch(
        f"{DOWNLOAD_MODULE}.get_page",
        return_value=html,
    ) as get_page_mock:
        links = get_all_promo_full_links(max_pages=1)

    get_page_mock.assert_called_once_with(
        category_id=ShufersalPriceCategory.PROMOS_FULL,
        page=1,
    )
    assert len(links) == 1


def test_select_latest_daily_promo_full_snapshot_links_keeps_latest_per_store() -> None:
    selected = select_latest_daily_promo_full_snapshot_links(
        [PROMO_001_EARLIER, PROMO_001_LATEST, PROMO_002]
    )

    assert selected == [PROMO_001_LATEST, PROMO_002]


def test_download_promo_full_files_applies_max_files_after_snapshot_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        f"{DOWNLOAD_MODULE}.SHUFERSAL_PROMO_FULL_RAW_DATA_DIR",
        tmp_path,
    )

    with patch(
        f"{DOWNLOAD_MODULE}.requests.get",
        return_value=_FakeDownloadResponse(),
    ) as get:
        files = download_promo_full_files(
            [PROMO_001_LATEST, PROMO_002],
            max_files=1,
            skip_existing=False,
        )

    assert len(files) == 1
    assert files[0].name == Path(PROMO_001_LATEST).name
    assert get.call_count == 1
    assert files[0].parent == tmp_path
