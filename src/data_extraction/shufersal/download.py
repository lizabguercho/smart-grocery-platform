"""Shufersal PriceFull, Stores, and PromoFull file downloader via HTTP category pages."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.data_extraction.data_extraction_config import (
    DOWNLOAD_CHUNK_SIZE_BYTES,
    HTML_PARSER,
    PRICE_FULL_FILENAME_PREFIX,
    PROMO_FULL_FILE_LABEL,
    PROMO_FULL_FILENAME_PREFIX,
    SHUFERSAL_CATEGORY_URL,
    SHUFERSAL_DEFAULT_STORE_ID,
    SHUFERSAL_DOWNLOAD_TIMEOUT_SECONDS,
    SHUFERSAL_PAGE_TIMEOUT_SECONDS,
    SHUFERSAL_PARAM_CATEGORY_ID,
    SHUFERSAL_PARAM_PAGE,
    SHUFERSAL_PARAM_STORE_ID,
    SHUFERSAL_PRICE_FULL_RAW_DATA_DIR,
    SHUFERSAL_PROMO_FULL_RAW_DATA_DIR,
    SHUFERSAL_STORES_RAW_DATA_DIR,
    SKIP_EXISTING_DOWNLOADS,
    STORES_FILE_LABEL,
    STORES_FILENAME_PREFIX,
    ShufersalPriceCategory,
)
from src.data_extraction.snapshots import (
    DailySnapshot,
    parse_price_full_filename,
    parse_promo_full_filename,
    parse_stores_filename,
    select_latest_daily_snapshots,
)


def get_page(
    category_id: ShufersalPriceCategory = ShufersalPriceCategory.PRICES_FULL,
    store_id: int = SHUFERSAL_DEFAULT_STORE_ID,
    page: int = 1,
) -> str:
    response = requests.get(
        SHUFERSAL_CATEGORY_URL,
        params={
            SHUFERSAL_PARAM_CATEGORY_ID: category_id.value,
            SHUFERSAL_PARAM_STORE_ID: store_id,
            SHUFERSAL_PARAM_PAGE: page,
        },
        timeout=SHUFERSAL_PAGE_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.text


def extract_download_prices_full_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, HTML_PARSER)
    return [
        urljoin(SHUFERSAL_CATEGORY_URL, link["href"])
        for link in soup.find_all("a", href=True)
        if PRICE_FULL_FILENAME_PREFIX in link["href"].lower()
    ]


def get_all_price_full_links(max_pages: int | None = None) -> list[str]:
    """Collect PriceFull download links from Shufersal listing pages.

    Stops when a page adds no new filenames (SAS query params can change
    even when the same files are repeated).

    ``max_pages=None`` means scan the full catalog.
    A limited ``max_pages`` value is for development only.
    """
    all_links = []
    seen_filenames = set()
    page = 1

    while True:
        if max_pages is not None and page > max_pages:
            break

        print(f"Reading page {page}...", flush=True)

        html = get_page(page=page)
        links = extract_download_prices_full_links(html)

        if not links:
            break

        new_links = []
        for link in links:
            filename = Path(urlparse(link).path).name
            if filename in seen_filenames:
                continue
            seen_filenames.add(filename)
            new_links.append(link)

        # Later pages can repeat the same leftover files with new SAS signatures.
        if not new_links:
            print(
                f"Stopping pagination: page {page} had no new PriceFull filenames.",
                flush=True,
            )
            break

        all_links.extend(new_links)
        page += 1

    return all_links


def extract_download_stores_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, HTML_PARSER)
    return [
        urljoin(SHUFERSAL_CATEGORY_URL, link["href"])
        for link in soup.find_all("a", href=True)
        if STORES_FILENAME_PREFIX in link["href"].lower()
    ]


def extract_download_promo_full_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, HTML_PARSER)
    return [
        urljoin(SHUFERSAL_CATEGORY_URL, link["href"])
        for link in soup.find_all("a", href=True)
        if PROMO_FULL_FILENAME_PREFIX in link["href"].lower()
    ]


def get_all_stores_links(max_pages: int | None = None) -> list[str]:
    """Collect Stores download links from Shufersal listing pages.

    ``max_pages=None`` means scan the full catalog.
    A limited ``max_pages`` value is for development only.
    """
    all_links = []
    seen_filenames = set()
    page = 1

    while True:
        if max_pages is not None and page > max_pages:
            break

        print(f"Reading page {page}...", flush=True)

        html = get_page(category_id=ShufersalPriceCategory.STORES, page=page)
        links = extract_download_stores_links(html)

        if not links:
            break

        new_links = []
        for link in links:
            filename = Path(urlparse(link).path).name
            if filename in seen_filenames:
                continue
            seen_filenames.add(filename)
            new_links.append(link)

        if not new_links:
            print(
                f"Stopping pagination: page {page} had no new "
                f"{STORES_FILE_LABEL} filenames.",
                flush=True,
            )
            break

        all_links.extend(new_links)
        page += 1

    return all_links


def get_all_promo_full_links(max_pages: int | None = None) -> list[str]:
    """Collect PromoFull download links from Shufersal listing pages.

    ``max_pages=None`` means scan the full catalog.
    A limited ``max_pages`` value is for development only.
    """
    all_links = []
    seen_filenames = set()
    page = 1

    while True:
        if max_pages is not None and page > max_pages:
            break

        print(f"Reading page {page}...", flush=True)

        html = get_page(category_id=ShufersalPriceCategory.PROMOS_FULL, page=page)
        links = extract_download_promo_full_links(html)

        if not links:
            break

        new_links = []
        for link in links:
            filename = Path(urlparse(link).path).name
            if filename in seen_filenames:
                continue
            seen_filenames.add(filename)
            new_links.append(link)

        if not new_links:
            print(
                f"Stopping pagination: page {page} had no new "
                f"{PROMO_FULL_FILE_LABEL} filenames.",
                flush=True,
            )
            break

        all_links.extend(new_links)
        page += 1

    return all_links


def _snapshots_from_links(
    links: list[str],
    parse_filename: Callable[[str], tuple[str, str, str] | None],
) -> list[DailySnapshot[str]]:
    snapshots: list[DailySnapshot[str]] = []
    for link in links:
        filename = Path(urlparse(link).path).name
        fields = parse_filename(filename)
        if fields is None:
            continue

        store_id, date, time = fields
        snapshots.append(
            DailySnapshot(
                store_id=store_id,
                date=date,
                time=time,
                payload=link,
            )
        )
    return snapshots


def select_latest_daily_snapshot_links(links: list[str]) -> list[str]:
    """Keep the latest PriceFull link per store for the latest available date."""
    selected = select_latest_daily_snapshots(
        _snapshots_from_links(links, parse_price_full_filename)
    )
    return [snapshot.payload for snapshot in selected]


def select_latest_daily_store_snapshot_links(links: list[str]) -> list[str]:
    """Keep the latest Stores link per store for the latest available date."""
    selected = select_latest_daily_snapshots(
        _snapshots_from_links(links, parse_stores_filename)
    )
    return [snapshot.payload for snapshot in selected]


def select_latest_daily_promo_full_snapshot_links(links: list[str]) -> list[str]:
    """Keep the latest PromoFull link per store for the latest available date."""
    selected = select_latest_daily_snapshots(
        _snapshots_from_links(links, parse_promo_full_filename)
    )
    return [snapshot.payload for snapshot in selected]


def _download_selected_links(
    links: list[str],
    output_dir: Path,
    *,
    max_files: int | None,
    skip_existing: bool,
    select_links: Callable[[list[str]], list[str]],
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_links = select_links(links)

    if max_files is not None:
        selected_links = selected_links[:max_files]

    downloaded_files = []

    for link in selected_links:
        filename = Path(urlparse(link).path).name

        if not filename:
            raise ValueError(f"Could not extract filename from URL: {link}")

        output_path = output_dir / filename

        if skip_existing and output_path.exists():
            print(f"Skipping existing file: {output_path.name}", flush=True)
            downloaded_files.append(output_path)
            continue

        with requests.get(
            link,
            timeout=SHUFERSAL_DOWNLOAD_TIMEOUT_SECONDS,
            stream=True,
        ) as response:
            response.raise_for_status()

            with output_path.open("wb") as file:
                for chunk in response.iter_content(
                    chunk_size=DOWNLOAD_CHUNK_SIZE_BYTES
                ):
                    if chunk:
                        file.write(chunk)

        downloaded_files.append(output_path)

    return downloaded_files


def download_files(
    links: list[str],
    *,
    max_files: int | None = None,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    return _download_selected_links(
        links,
        SHUFERSAL_PRICE_FULL_RAW_DATA_DIR,
        max_files=max_files,
        skip_existing=skip_existing,
        select_links=select_latest_daily_snapshot_links,
    )


def download_store_files(
    links: list[str],
    *,
    max_files: int | None = None,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    return _download_selected_links(
        links,
        SHUFERSAL_STORES_RAW_DATA_DIR,
        max_files=max_files,
        skip_existing=skip_existing,
        select_links=select_latest_daily_store_snapshot_links,
    )


def download_promo_full_files(
    links: list[str],
    *,
    max_files: int | None = None,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    return _download_selected_links(
        links,
        SHUFERSAL_PROMO_FULL_RAW_DATA_DIR,
        max_files=max_files,
        skip_existing=skip_existing,
        select_links=select_latest_daily_promo_full_snapshot_links,
    )
