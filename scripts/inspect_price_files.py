from src.data_extraction.data_extraction_config import (
    PRICE_FULL_FILE_GLOB,
    RAW_DATA_DIR,
)


def main() -> None:
    price_full_files = sorted(RAW_DATA_DIR.glob(PRICE_FULL_FILE_GLOB))
    print(f"Found {len(price_full_files)} PriceFull files:\n")

    for file in price_full_files:
        print(file.name)


if __name__ == "__main__":
    main()
