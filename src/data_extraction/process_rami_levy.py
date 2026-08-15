from pathlib import Path

from .data_extraction_config import (
    RAMI_LEVY_CHAIN_NAME,
    RAMI_LEVY_RAW_DATA_DIR,
)
from . import utils
from .models import PriceFullProduct
from .price_full_parser import parse_price_full_files
from .rami_levy.download import download_price_full_files
from src.database_loader.loader import (
    load_products_to_staging,
    load_products,
    load_product_prices,
    clear_staging,
)
from src.database_loader.validation import validate_staging, validate_product_prices


def get_local_price_files() -> list[Path]:
    RAMI_LEVY_RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(RAMI_LEVY_RAW_DATA_DIR.glob("*PriceFull*"))


def main(
    *,
    download: bool = True,
    max_files: int | None = 3,
) -> list[PriceFullProduct]:
    if download:
        print("1. Getting Rami Levy PriceFull files...", flush=True)
        print("2. Downloading files...", flush=True)
        # Default is 3 for development. Pass max_files=None later to download all files.
        downloaded_files = download_price_full_files(max_files=max_files)
        print(f"Using {len(downloaded_files)} files.", flush=True)
    else:
        print("Skipping download. Using local files only...", flush=True)
        downloaded_files = get_local_price_files()
        print(f"Found {len(downloaded_files)} local files.", flush=True)

        if not downloaded_files:
            raise FileNotFoundError(
                f"No PriceFull files found in {RAMI_LEVY_RAW_DATA_DIR}. "
                "Run with download=True first, or place files there manually."
            )

    print("3. Parsing product files...", flush=True)
    products = parse_price_full_files(downloaded_files)
    print(f"Parsed {len(products)} product records.", flush=True)

    print("4. Saving CSV...", flush=True)
    utils.save_to_csv(products, RAMI_LEVY_CHAIN_NAME)
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

    return products


if __name__ == "__main__":
    main()
