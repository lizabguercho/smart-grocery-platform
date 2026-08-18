from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from src.data_extraction.data_extraction_config import GZIP_EXTENSION
from src.data_extraction.models import Store
from src.data_extraction.snapshots import parse_stores_filename


def extract_date_from_store_filename(file_path: Path) -> str:
    parsed = parse_stores_filename(file_path.name)
    if parsed is None:
        raise ValueError(f"Unexpected filename format: {file_path.name}")

    _, date_text, _ = parsed
    date_text = date_text[:8]
    try:
        if len(date_text) != 8:
            raise ValueError
        extraction_date = date(
            int(date_text[0:4]),
            int(date_text[4:6]),
            int(date_text[6:8]),
        )
    except (TypeError, ValueError):
        raise ValueError(f"Invalid date '{date_text}' in filename: {file_path.name}")

    return extraction_date.isoformat()


def parse_store_file(file_path: Path) -> list[Store]:
    if file_path.name.lower().endswith(GZIP_EXTENSION):
        with gzip.open(file_path, "rt", encoding="utf-8") as xml_file:
            tree = ET.parse(xml_file)
    else:
        tree = ET.parse(file_path)

    root = tree.getroot()
    chain_id = root.findtext("ChainID")
    chain_name = root.findtext("ChainName")
    extraction_date = extract_date_from_store_filename(file_path)
    sub_chains = root.find("SubChains")
    if sub_chains is None:
        return []

    stores = []
    for sub_chain in sub_chains.findall("SubChain"):
        sub_chain_id = sub_chain.findtext("SubChainID") or sub_chain.findtext(
            "SubChainId"
        )
        sub_chain_name = sub_chain.findtext("SubChainName")
        stores_element = sub_chain.find("Stores")
        if stores_element is None:
            continue

        for store_element in stores_element.findall("Store"):
            stores.append(
                Store.from_xml(
                    store_element,
                    chain_id=chain_id,
                    chain_name=chain_name,
                    sub_chain_id=sub_chain_id,
                    sub_chain_name=sub_chain_name,
                    source_file=file_path.name,
                    extraction_date=extraction_date,
                )
            )
    return stores


def parse_store_files(downloaded_files: list[Path]) -> list[Store]:
    stores: list[Store] = []
    skipped_files = 0

    for file_path in downloaded_files:
        try:
            parsed = parse_store_file(file_path)
        except (gzip.BadGzipFile, ET.ParseError, OSError, ValueError) as error:
            skipped_files += 1
            print(f"Skipping unreadable file {file_path.name}: {error}", flush=True)
            continue

        if not parsed:
            skipped_files += 1
            print(f"Skipping file with no stores: {file_path.name}", flush=True)
            continue

        stores.extend(parsed)

    if skipped_files:
        print(f"Skipped {skipped_files} file(s) due to parse errors.", flush=True)

    return stores
