import gzip
from pathlib import Path

import pytest

from src.data_extraction.price_full_parser import (
    extract_date_from_filename,
    parse_price_full_files,
)

VALID_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<Root>
  <StoreID>001</StoreID>
  <ChainID>7290027600007</ChainID>
  <SubChainID>001</SubChainID>
  <Items>
    <Item>
      <ItemCode>123</ItemCode>
      <ItemName>Milk</ItemName>
      <bIsWeighted>0</bIsWeighted>
      <QtyInPackage>1</QtyInPackage>
    </Item>
  </Items>
</Root>
"""

NO_ITEMS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<Root>
  <StoreID>001</StoreID>
  <ChainID>7290027600007</ChainID>
  <SubChainID>001</SubChainID>
</Root>
"""


def _write_gzip_xml(directory: Path, name: str, xml: str) -> Path:
    path = directory / name
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(xml)
    return path


def test_extract_date_from_filename_returns_iso_date() -> None:
    path = Path("PriceFull7290027600007-001-001-20260722-030000.gz")
    assert extract_date_from_filename(path) == "2026-07-22"


def test_extract_date_from_filename_rejects_short_names() -> None:
    with pytest.raises(ValueError, match="Unexpected filename format"):
        extract_date_from_filename(Path("PriceFull.gz"))


def test_extract_date_from_filename_rejects_invalid_dates() -> None:
    with pytest.raises(ValueError, match="Invalid date"):
        extract_date_from_filename(
            Path("PriceFull7290027600007-001-001-20261399-030000.gz")
        )


def test_parse_price_full_files_reads_gzip_xml(tmp_path: Path) -> None:
    path = _write_gzip_xml(
        tmp_path,
        "PriceFull7290027600007-001-001-20260722-030000.gz",
        VALID_XML,
    )

    products = parse_price_full_files([path])

    assert len(products) == 1
    assert products[0].item_code == "123"
    assert products[0].item_name == "Milk"
    assert products[0].store_id == "001"
    assert products[0].chain_id == "7290027600007"
    assert products[0].extraction_date == "2026-07-22"
    assert products[0].source_file == path.name


def test_parse_price_full_files_skips_files_without_items(tmp_path: Path) -> None:
    path = _write_gzip_xml(
        tmp_path,
        "PriceFull7290027600007-001-001-20260722-030000.gz",
        NO_ITEMS_XML,
    )

    assert parse_price_full_files([path]) == []


def test_parse_price_full_files_skips_unreadable_gzip(tmp_path: Path) -> None:
    path = tmp_path / "PriceFull7290027600007-001-001-20260722-030000.gz"
    path.write_bytes(b"not gzip")

    assert parse_price_full_files([path]) == []
