from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from .models import FileMetadata, PriceFullProduct


def extract_date_from_filename(file_path: Path) -> str:
    filename = file_path.stem
    parts = filename.split("-")

    # Expected format:
    # PriceFull7290027600007-001-001-20260722-030000

    if len(parts) < 5:
        raise ValueError(f"Unexpected filename format: {file_path.name}")

    date_text = parts[-2]

    try:
        extraction_date = datetime.strptime(date_text, "%Y%m%d").date()
    except ValueError:
        raise ValueError(f"Invalid date '{date_text}' in filename: {file_path.name}")

    return extraction_date.isoformat()


def parse_price_full_files(downloaded_files: list[Path]) -> list[PriceFullProduct]:
    products = []
    skipped_files = 0

    for file_path in downloaded_files:
        try:
            with gzip.open(file_path, "rt", encoding="utf-8") as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()
        except (gzip.BadGzipFile, ET.ParseError, OSError, ValueError) as error:
            skipped_files += 1
            print(f"Skipping unreadable file {file_path.name}: {error}", flush=True)
            continue

        file_metadata = FileMetadata(
            store_id=root.findtext("StoreID"),
            chain_id=root.findtext("ChainID"),
            sub_chain_id=root.findtext("SubChainID"),
            extraction_date=extract_date_from_filename(file_path),
            source_file=file_path.name,
        )

        items = root.find("Items")

        if items is None:
            skipped_files += 1
            print(f"Skipping file with no items: {file_path.name}", flush=True)
            continue

        for item in items:
            products.append(
                PriceFullProduct.from_xml(
                    item=item,
                    file_metadata=file_metadata,
                )
            )

    if skipped_files:
        print(f"Skipped {skipped_files} file(s) due to parse errors.", flush=True)

    return products
