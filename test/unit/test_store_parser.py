import gzip
from pathlib import Path

import pytest

from src.data_extraction.store_parser import (
    extract_date_from_store_filename,
    parse_store_files,
)

VALID_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<Chain>
  <ChainID>7290027600007</ChainID>
  <ChainName>Shufersal</ChainName>
  <SubChains>
    <SubChain>
      <SubChainID>1</SubChainID>
      <SubChainName>Shufersal Sheli</SubChainName>
      <Stores>
        <Store>
          <StoreID>756</StoreID>
          <BikoretNo>7</BikoretNo>
          <StoreType>1</StoreType>
          <StoreName>Sheli Beer Yaakov</StoreName>
          <Address>17 Yitzhak Shamir</Address>
          <City>2530</City>
          <ZIPCode>7030336</ZIPCode>
        </Store>
      </Stores>
    </SubChain>
  </SubChains>
</Chain>
"""

NO_STORES_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<Chain>
  <ChainID>7290027600007</ChainID>
  <ChainName>Shufersal</ChainName>
</Chain>
"""


def _write_gzip_xml(directory: Path, name: str, xml: str) -> Path:
    path = directory / name
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(xml)
    return path


def test_extract_date_from_store_filename_returns_iso_date() -> None:
    path = Path("Stores7290027600007-000-20260816-020.gz")
    assert extract_date_from_store_filename(path) == "2026-08-16"


def test_extract_date_from_store_filename_reads_packed_victory_datetime() -> None:
    path = Path("Stores7290696200003-000-20260816060100-060100.gz")
    assert extract_date_from_store_filename(path) == "2026-08-16"


def test_extract_date_from_store_filename_rejects_non_stores_names() -> None:
    with pytest.raises(ValueError, match="Unexpected filename format"):
        extract_date_from_store_filename(
            Path("PriceFull7290027600007-001-001-20260722-030000.gz")
        )


def test_parse_store_files_treats_blank_store_type_as_null(tmp_path: Path) -> None:
    xml = VALID_XML.replace("<StoreType>1</StoreType>", "<StoreType></StoreType>")
    path = _write_gzip_xml(
        tmp_path,
        "Stores7290696200003-000-20260816060100-060100.gz",
        xml,
    )

    stores = parse_store_files([path])

    assert len(stores) == 1
    assert stores[0].store_type is None


def test_parse_store_files_reads_gzip_xml(tmp_path: Path) -> None:
    path = _write_gzip_xml(
        tmp_path,
        "Stores7290027600007-000-20260816-020.gz",
        VALID_XML,
    )

    stores = parse_store_files([path])

    assert len(stores) == 1
    assert stores[0].chain_id == "7290027600007"
    assert stores[0].chain_name == "Shufersal"
    assert stores[0].sub_chain_id == "1"
    assert stores[0].sub_chain_name == "Shufersal Sheli"
    assert stores[0].store_id == "756"
    assert stores[0].store_name == "Sheli Beer Yaakov"
    assert stores[0].city == "2530"
    assert stores[0].zip_code == "7030336"
    assert stores[0].extraction_date == "2026-08-16"
    assert stores[0].source_file == path.name


def test_parse_store_files_reads_plain_xml(tmp_path: Path) -> None:
    path = tmp_path / "Stores7290058140886-000-20260816-050500.xml"
    path.write_text(VALID_XML, encoding="utf-8")

    stores = parse_store_files([path])

    assert len(stores) == 1
    assert stores[0].store_id == "756"
    assert stores[0].extraction_date == "2026-08-16"
    assert stores[0].source_file == path.name


def test_parse_store_files_skips_files_without_stores(tmp_path: Path) -> None:
    path = _write_gzip_xml(
        tmp_path,
        "Stores7290027600007-000-20260816-020.gz",
        NO_STORES_XML,
    )

    assert parse_store_files([path]) == []


def test_parse_store_files_skips_unreadable_gzip(tmp_path: Path) -> None:
    path = tmp_path / "Stores7290027600007-000-20260816-020.gz"
    path.write_bytes(b"not gzip")

    assert parse_store_files([path]) == []
