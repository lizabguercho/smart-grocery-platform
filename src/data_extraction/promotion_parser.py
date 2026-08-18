from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from src.data_extraction.data_extraction_config import (
    GZIP_EXTENSION,
    RAMI_LEVY_CHAIN_ID,
)
from src.data_extraction.models import Promotion, PromotionGroup, PromotionItem
from src.data_extraction.snapshots import (
    is_unsupported_rami_levy_promo_filename,
    is_unsupported_rami_levy_store_id,
    parse_promo_full_filename,
)


def extract_date_from_promo_full_filename(file_path: Path) -> str:
    parsed = parse_promo_full_filename(file_path.name)
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


def _is_unsupported_rami_levy_store(
    chain_id: str | None,
    store_id: str | None,
) -> bool:
    if chain_id is None or chain_id.strip() != RAMI_LEVY_CHAIN_ID:
        return False
    return is_unsupported_rami_levy_store_id(store_id)


def _open_promo_full_tree(file_path: Path) -> ET.ElementTree:
    if file_path.name.lower().endswith(GZIP_EXTENSION):
        with gzip.open(file_path, "rt", encoding="utf-8-sig") as xml_file:
            return ET.parse(xml_file)

    with file_path.open("rt", encoding="utf-8-sig") as xml_file:
        return ET.parse(xml_file)


def parse_promo_full_file(file_path: Path) -> list[Promotion]:
    if is_unsupported_rami_levy_promo_filename(file_path.name):
        print(
            f"Skipping unsupported Rami Levy store 039 file: {file_path.name}",
            flush=True,
        )
        return []

    tree = _open_promo_full_tree(file_path)
    root = tree.getroot()

    # Root metadata is shared by every promotion in this file.
    chain_id = root.findtext("ChainID")
    sub_chain_id = root.findtext("SubChainID")
    store_id = root.findtext("StoreID")
    bikoret_no = root.findtext("BikoretNo")

    if _is_unsupported_rami_levy_store(chain_id, store_id):
        print(
            f"Skipping unsupported Rami Levy store 039 file: {file_path.name}",
            flush=True,
        )
        return []

    extraction_date = extract_date_from_promo_full_filename(file_path)
    promotions_element = root.find("Promotions")
    if promotions_element is None:
        return []

    promotions: list[Promotion] = []

    # Level 1: each Promotion under Promotions.
    for promotion_element in promotions_element.findall("Promotion"):
        groups: list[PromotionGroup] = []
        groups_element = promotion_element.find("Groups")

        # Level 2: each Group under Groups.
        if groups_element is not None:
            for group_element in groups_element.findall("Group"):
                items: list[PromotionItem] = []
                promotion_items_element = group_element.find("PromotionItems")

                # Level 3: each PromotionItem under PromotionItems.
                if promotion_items_element is not None:
                    for item_element in promotion_items_element.findall(
                        "PromotionItem"
                    ):
                        items.append(PromotionItem.from_xml(item_element))

                groups.append(PromotionGroup.from_xml(group_element, items))

        promotions.append(
            Promotion.from_xml(
                promotion_element,
                chain_id=chain_id,
                sub_chain_id=sub_chain_id,
                store_id=store_id,
                bikoret_no=bikoret_no,
                source_file=file_path.name,
                extraction_date=extraction_date,
                groups=groups,
            )
        )

    return promotions


def parse_promo_full_files(downloaded_files: list[Path]) -> list[Promotion]:
    promotions: list[Promotion] = []
    skipped_files = 0

    for file_path in downloaded_files:
        try:
            parsed = parse_promo_full_file(file_path)
        except (gzip.BadGzipFile, ET.ParseError, OSError, ValueError) as error:
            skipped_files += 1
            print(f"Skipping unreadable file {file_path.name}: {error}", flush=True)
            continue

        if not parsed:
            skipped_files += 1
            print(
                f"Skipping file with no promotions: {file_path.name}",
                flush=True,
            )
            continue

        promotions.extend(parsed)

    if skipped_files:
        print(f"Skipped {skipped_files} file(s) due to parse errors.", flush=True)

    return promotions
