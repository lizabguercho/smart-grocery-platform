from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.database_loader.loader import (
    clear_staging,
    load_product_prices,
    load_products,
    load_products_to_staging,
)
from src.database_loader.validation import validate_product_prices, validate_staging

from . import utils
from .data_extraction_config import (
    RAW_DATA_DIR,
    SHUFERSAL_CATEGORY_URL,
    SHUFERSAL_CHAIN_NAME,
    SKIP_EXISTING_DOWNLOADS,
    ShufersalPriceCategory,
)
from .models import PriceFullProduct
from .price_full_parser import parse_price_full_files


# downloads the webpage and returns the HTML as a string.
def get_page(
    category_id: ShufersalPriceCategory = ShufersalPriceCategory.PRICES_FULL,
    store_id: int = 0,
    page: int = 1,
):
    response = requests.get(
        SHUFERSAL_CATEGORY_URL,
        params={
            "catID": category_id.value,
            "storeId": store_id,
            "page": page,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


# parses that HTML and extracts the download URLs, which it returns as a list of strings.
def extract_download_prices_full_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        urljoin(SHUFERSAL_CATEGORY_URL, link["href"])
        for link in soup.find_all("a", href=True)
        if "pricefull" in link["href"].lower()
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


def _parse_price_full_filename(name: str) -> tuple[str, str, str] | None:
    """Return (store_id, date, time) from a PriceFull filename, or None."""
    # Expected: PriceFull{chain}-{sub}-{store}-{YYYYMMDD}-{HHMMSS}.gz
    if not name.lower().startswith("pricefull") or not name.lower().endswith(".gz"):
        return None

    stem = name[:-3]  # remove .gz
    parts = stem.split("-")
    if len(parts) < 5:
        return None

    store_id = parts[-3]
    date = parts[-2]
    time = parts[-1]
    return store_id, date, time


def _select_latest_daily_snapshots(links: list[str]) -> list[str]:
    """Keep the latest PriceFull link per store for the latest available date."""

    # Step 1: Parse each PriceFull link filename into store_id, date, and time.
    parsed_files = []
    for link in links:
        filename = Path(urlparse(link).path).name
        fields = _parse_price_full_filename(filename)
        if fields is None:
            continue

        store_id, date, time = fields
        parsed_files.append(
            {
                "store_id": store_id,
                "date": date,
                "time": time,
                "filename": filename,
                "link": link,
            }
        )

    if not parsed_files:
        return []

    # Step 2: Find the latest date available across all PriceFull files.
    latest_date = parsed_files[0]["date"]
    for file_info in parsed_files:
        latest_date = max(latest_date, file_info["date"])

    # Step 3: Keep only files from that latest date.
    same_day_files = []
    for file_info in parsed_files:
        if file_info["date"] == latest_date:
            same_day_files.append(file_info)

    # Step 4: For each store, keep the file with the latest time.
    latest_file_by_store = {}
    for file_info in same_day_files:
        store_id = file_info["store_id"]
        time = file_info["time"]

        if store_id not in latest_file_by_store:
            latest_file_by_store[store_id] = file_info
            continue

        current_best_time = latest_file_by_store[store_id]["time"]
        if time > current_best_time:
            latest_file_by_store[store_id] = file_info

    selected_links = []
    for store_id in sorted(latest_file_by_store):
        selected_links.append(latest_file_by_store[store_id]["link"])

    print(
        f"Latest date {latest_date}: selected {len(selected_links)} store snapshot(s).",
        flush=True,
    )
    return selected_links


# downloads the files from the links and saves them to the current directory.
def download_files(
    links: list[str],
    *,
    max_files: int | None = None,
    skip_existing: bool = SKIP_EXISTING_DOWNLOADS,
) -> list[Path]:
    output_dir = RAW_DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Select one latest snapshot per store for the latest date first.
    selected_links = _select_latest_daily_snapshots(links)

    # Development limit applies only after deduplication.
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

        with requests.get(link, timeout=60, stream=True) as response:
            response.raise_for_status()

            with output_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)

        downloaded_files.append(output_path)

    return downloaded_files


def get_local_price_files() -> list[Path]:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(RAW_DATA_DIR.glob("*PriceFull*"))


# main function that downloads the files from the links and saves them to the current directory. It calls the other functions in the correct order.
def main(
    *,
    download: bool = True,
    max_files: int | None = 3,
    max_pages: int | None = 2,
) -> list[PriceFullProduct]:
    if download:
        print("1. Getting Shufersal download links...", flush=True)
        # Development defaults: max_pages=2, max_files=3.
        # Full catalog: main(max_pages=None, max_files=None)
        links = get_all_price_full_links(max_pages=max_pages)
        print(f"Found {len(links)} links.", flush=True)

        print("2. Downloading files...", flush=True)
        downloaded_files = download_files(links, max_files=max_files)
        print(f"Using {len(downloaded_files)} files.", flush=True)
    else:
        print("Skipping download. Using local files only...", flush=True)
        downloaded_files = get_local_price_files()
        print(f"Found {len(downloaded_files)} local files.", flush=True)

        if not downloaded_files:
            raise FileNotFoundError(
                f"No PriceFull files found in {RAW_DATA_DIR}. "
                "Run with download=True first, or place files there manually."
            )

    print("3. Parsing product files...", flush=True)
    products = parse_price_full_files(downloaded_files)
    print(f"Parsed {len(products)} product records.", flush=True)

    print("4. Saving CSV...", flush=True)
    utils.save_to_csv(products, SHUFERSAL_CHAIN_NAME)
    print("CSV saved successfully.", flush=True)

    print("5. Loading data into staging...", flush=True)
    load_products_to_staging(products)

    print("6. Validating staging data...", flush=True)
    validate_staging()

    print("7. Loading products...", flush=True)
    load_products()

    print("8. Loading product prices...", flush=True)
    load_product_prices()

    print("9. Validating product prices...", flush=True)
    validate_product_prices()
    print("10. Clearing staging...", flush=True)
    clear_staging()


if __name__ == "__main__":
    main()
