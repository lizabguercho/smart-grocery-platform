import xml.etree.ElementTree as ET

from src.data_extraction.models import (
    FileMetadata,
    PriceFullProduct,
    normalize_int_text,
)


def test_normalize_int_text_returns_none_for_blank_and_unknown() -> None:
    assert normalize_int_text(None) is None
    assert normalize_int_text("") is None
    assert normalize_int_text("   ") is None
    assert normalize_int_text("לא ידוע") is None


def test_normalize_int_text_strips_valid_values() -> None:
    assert normalize_int_text("  12  ") == "12"


def test_from_xml_maps_item_fields_and_file_metadata() -> None:
    item = ET.Element("Item")
    ET.SubElement(item, "ItemCode").text = "123"
    ET.SubElement(item, "ItemName").text = "Bread"
    ET.SubElement(item, "bIsWeighted").text = "1"
    ET.SubElement(item, "QtyInPackage").text = "לא ידוע"

    metadata = FileMetadata(
        store_id="001",
        chain_id="7290027600007",
        sub_chain_id="002",
        extraction_date="2026-07-22",
        source_file="example.gz",
    )

    product = PriceFullProduct.from_xml(item, metadata)

    assert product.item_code == "123"
    assert product.item_name == "Bread"
    assert product.is_weighted == "1"
    assert product.qty_in_package is None
    assert product.store_id == "001"
    assert product.chain_id == "7290027600007"
    assert product.sub_chain_id == "002"
    assert product.source_file == "example.gz"
    assert product.extraction_date == "2026-07-22"


def test_from_xml_falls_back_to_is_weighted_tag() -> None:
    item = ET.Element("Item")
    ET.SubElement(item, "IsWeighted").text = "0"
    metadata = FileMetadata(
        store_id=None,
        chain_id=None,
        sub_chain_id=None,
        extraction_date="2026-01-01",
        source_file="other.gz",
    )

    product = PriceFullProduct.from_xml(item, metadata)

    assert product.is_weighted == "0"
