import gzip
from pathlib import Path

import pytest

from src.data_extraction.promotion_parser import (
    extract_date_from_promo_full_filename,
    parse_promo_full_files,
)

VALID_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<Root>
  <ChainID>7290027600007</ChainID>
  <SubChainID>001</SubChainID>
  <StoreID>001</StoreID>
  <BikoretNo>1</BikoretNo>
  <Promotions>
    <Promotion>
      <PromotionID>100</PromotionID>
      <PromotionDescription>Buy 2 get 1</PromotionDescription>
      <PromotionStartDateTime>2026-08-01 00:00:00</PromotionStartDateTime>
      <PromotionEndDateTime>2026-08-31 23:59:00</PromotionEndDateTime>
      <PromotionStartHour>0000</PromotionStartHour>
      <PromotionEndHour>2359</PromotionEndHour>
      <PromotionUpdateTime>2026-08-16 03:00:00</PromotionUpdateTime>
      <AllowMultipleDiscounts>1</AllowMultipleDiscounts>
      <ClubID>0</ClubID>
      <MinNoOfItemOffered>1</MinNoOfItemOffered>
      <RedemptionLimit>0</RedemptionLimit>
      <IsGiftItem>0</IsGiftItem>
      <AdditionalIsCoupon>0</AdditionalIsCoupon>
      <AdditionalRestrictions></AdditionalRestrictions>
      <Remarks></Remarks>
      <PromotionDays>1111111</PromotionDays>
      <Groups>
        <Group>
          <GroupID>1</GroupID>
          <MinPurchaseAmount>20</MinPurchaseAmount>
          <DiscountType>1</DiscountType>
          <PromotionItems>
            <PromotionItem>
              <ItemCode>123</ItemCode>
              <ItemType>1</ItemType>
              <bIsWeighted>0</bIsWeighted>
              <RewardType>1</RewardType>
              <MinQty>1</MinQty>
              <MaxQty>10</MaxQty>
              <DiscountedPrice>5.90</DiscountedPrice>
              <DiscountedPricePerMida>5.90</DiscountedPricePerMida>
              <DiscountRate>10</DiscountRate>
            </PromotionItem>
          </PromotionItems>
        </Group>
      </Groups>
    </Promotion>
  </Promotions>
</Root>
"""

NO_PROMOTIONS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<Root>
  <ChainID>7290027600007</ChainID>
  <SubChainID>001</SubChainID>
  <StoreID>001</StoreID>
</Root>
"""

RAMI_LEVY_039_XML = VALID_XML.replace(
    "<ChainID>7290027600007</ChainID>",
    "<ChainID>7290058140886</ChainID>",
).replace(
    "<StoreID>001</StoreID>",
    "<StoreID>039</StoreID>",
)


def _write_gzip_xml(directory: Path, name: str, xml: str) -> Path:
    path = directory / name
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(xml)
    return path


def test_extract_date_from_promo_full_filename_returns_iso_date() -> None:
    path = Path("PromoFull7290027600007-001-001-20260816-030000.gz")
    assert extract_date_from_promo_full_filename(path) == "2026-08-16"


def test_extract_date_from_promo_full_filename_rejects_non_promo_names() -> None:
    with pytest.raises(ValueError, match="Unexpected filename format"):
        extract_date_from_promo_full_filename(
            Path("PriceFull7290027600007-001-001-20260722-030000.gz")
        )


def test_parse_promo_full_files_builds_promotion_group_item_hierarchy(
    tmp_path: Path,
) -> None:
    path = _write_gzip_xml(
        tmp_path,
        "PromoFull7290027600007-001-001-20260816-030000.gz",
        VALID_XML,
    )

    promotions = parse_promo_full_files([path])

    assert len(promotions) == 1
    promotion = promotions[0]
    assert promotion.chain_id == "7290027600007"
    assert promotion.sub_chain_id == "001"
    assert promotion.store_id == "001"
    assert promotion.bikoret_no == "1"
    assert promotion.promotion_id == "100"
    assert promotion.promotion_description == "Buy 2 get 1"
    assert promotion.club_id == "0"
    assert promotion.extraction_date == "2026-08-16"
    assert promotion.source_file == path.name
    assert len(promotion.groups) == 1
    group = promotion.groups[0]
    assert group.group_id == "1"
    assert group.min_purchase_amount == "20"
    assert group.discount_type == "1"
    assert len(group.items) == 1
    item = group.items[0]
    assert item.item_code == "123"
    assert item.item_type == "1"
    assert item.is_weighted == "0"
    assert item.reward_type == "1"
    assert item.min_qty == "1"
    assert item.discounted_price == "5.90"


def test_parse_promo_full_files_treats_blank_optional_tags_as_none(
    tmp_path: Path,
) -> None:
    xml = VALID_XML.replace("<Remarks></Remarks>", "<Remarks/>").replace(
        "<ClubID>0</ClubID>",
        "<ClubID></ClubID>",
    )
    path = _write_gzip_xml(
        tmp_path,
        "PromoFull7290027600007-001-001-20260816-030000.gz",
        xml,
    )

    promotions = parse_promo_full_files([path])

    assert promotions[0].club_id is None
    assert promotions[0].remarks is None


def test_parse_promo_full_files_handles_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "PromoFull7290027600007-001-001-20260816-030000.gz"
    with gzip.open(path, "wt", encoding="utf-8-sig") as handle:
        handle.write(VALID_XML)

    promotions = parse_promo_full_files([path])

    assert len(promotions) == 1
    assert promotions[0].promotion_id == "100"


def test_parse_promo_full_files_ignores_item_tags(tmp_path: Path) -> None:
    xml = VALID_XML.replace(
        "<PromotionItems>",
        "<PromotionItems><Item><ItemCode>999</ItemCode></Item>",
        1,
    )
    path = _write_gzip_xml(
        tmp_path,
        "PromoFull7290027600007-001-001-20260816-030000.gz",
        xml,
    )

    promotions = parse_promo_full_files([path])

    assert [item.item_code for item in promotions[0].groups[0].items] == ["123"]


def test_parse_promo_full_files_skips_files_without_promotions(
    tmp_path: Path,
) -> None:
    path = _write_gzip_xml(
        tmp_path,
        "PromoFull7290027600007-001-001-20260816-030000.gz",
        NO_PROMOTIONS_XML,
    )

    assert parse_promo_full_files([path]) == []


def test_parse_promo_full_files_skips_rami_levy_store_039(tmp_path: Path) -> None:
    path = _write_gzip_xml(
        tmp_path,
        "PromoFull7290058140886-001-039-20260816-030000.gz",
        RAMI_LEVY_039_XML,
    )

    assert parse_promo_full_files([path]) == []


def test_parse_promo_full_files_skips_unreadable_gzip(tmp_path: Path) -> None:
    path = tmp_path / "PromoFull7290027600007-001-001-20260816-030000.gz"
    path.write_bytes(b"not gzip")

    assert parse_promo_full_files([path]) == []
