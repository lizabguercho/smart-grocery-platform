import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class FileMetadata:
    store_id: str | None
    chain_id: str | None
    sub_chain_id: str | None
    extraction_date: str
    source_file: str


def normalize_int_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    if value in {"", "לא ידוע"}:
        return None

    return value


def optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()
    if value == "":
        return None

    return value


@dataclass
class PriceFullProduct:
    item_code: str | None
    item_name: str | None
    manufacture_name: str | None
    manufacture_country: str | None
    manufacture_item_description: str | None
    unit_qty: str | None
    quantity: str | None
    unit_of_measure: str | None
    is_weighted: str | None
    qty_in_package: str | None
    item_price: str | None
    unit_of_measure_price: str | None
    allow_discount: str | None
    item_status: str | None
    price_update_time: str | None
    last_sale_date_time: str | None
    item_type: str | None
    store_id: str | None
    chain_id: str | None
    sub_chain_id: str | None
    source_file: str
    extraction_date: str

    @classmethod
    def from_xml(
        cls, item: ET.Element, file_metadata: FileMetadata
    ) -> "PriceFullProduct":
        fields = {child.tag: child.text for child in item}

        return cls(
            item_code=fields.get("ItemCode"),
            item_name=fields.get("ItemName"),
            manufacture_name=fields.get("ManufactureName"),
            manufacture_country=fields.get("ManufactureCountry"),
            manufacture_item_description=fields.get("ManufactureItemDescription"),
            unit_qty=fields.get("UnitQty"),
            quantity=fields.get("Quantity"),
            unit_of_measure=fields.get("UnitOfMeasure"),
            is_weighted=fields.get("bIsWeighted") or fields.get("IsWeighted"),
            qty_in_package=normalize_int_text(fields.get("QtyInPackage")),
            item_price=fields.get("ItemPrice"),
            unit_of_measure_price=fields.get("UnitOfMeasurePrice"),
            allow_discount=fields.get("AllowDiscount"),
            item_status=fields.get("ItemStatus"),
            price_update_time=fields.get("PriceUpdateTime"),
            last_sale_date_time=fields.get("LastSaleDateTime"),
            item_type=fields.get("ItemType"),
            store_id=file_metadata.store_id,
            chain_id=file_metadata.chain_id,
            sub_chain_id=file_metadata.sub_chain_id,
            source_file=file_metadata.source_file,
            extraction_date=file_metadata.extraction_date,
        )


@dataclass
class Store:
    chain_id: str | None
    chain_name: str | None
    sub_chain_id: str | None
    sub_chain_name: str | None
    store_id: str | None
    bikoret_no: str | None
    store_type: str | None
    store_name: str | None
    address: str | None
    city: str | None
    zip_code: str | None
    source_file: str
    extraction_date: str

    @classmethod
    def from_xml(
        cls,
        store_element: ET.Element,
        *,
        chain_id: str | None,
        chain_name: str | None,
        sub_chain_id: str | None,
        sub_chain_name: str | None,
        source_file: str,
        extraction_date: str,
    ) -> "Store":
        return cls(
            chain_id=normalize_int_text(chain_id),
            chain_name=chain_name,
            sub_chain_id=normalize_int_text(sub_chain_id),
            sub_chain_name=sub_chain_name,
            store_id=normalize_int_text(store_element.findtext("StoreID")),
            bikoret_no=normalize_int_text(store_element.findtext("BikoretNo")),
            store_type=normalize_int_text(store_element.findtext("StoreType")),
            store_name=store_element.findtext("StoreName"),
            address=store_element.findtext("Address"),
            city=store_element.findtext("City"),
            zip_code=(
                store_element.findtext("ZIPCode") or store_element.findtext("ZipCode")
            ),
            source_file=source_file,
            extraction_date=extraction_date,
        )


@dataclass
class PromotionItem:
    item_code: str | None
    item_type: str | None
    is_weighted: str | None
    reward_type: str | None
    min_qty: str | None
    max_qty: str | None
    discounted_price: str | None
    discounted_price_per_mida: str | None
    discount_rate: str | None

    @classmethod
    def from_xml(cls, item_element: ET.Element) -> "PromotionItem":
        return cls(
            item_code=optional_text(item_element.findtext("ItemCode")),
            item_type=optional_text(item_element.findtext("ItemType")),
            is_weighted=optional_text(item_element.findtext("bIsWeighted")),
            reward_type=optional_text(item_element.findtext("RewardType")),
            min_qty=optional_text(item_element.findtext("MinQty")),
            max_qty=optional_text(item_element.findtext("MaxQty")),
            discounted_price=optional_text(item_element.findtext("DiscountedPrice")),
            discounted_price_per_mida=optional_text(
                item_element.findtext("DiscountedPricePerMida")
            ),
            discount_rate=optional_text(item_element.findtext("DiscountRate")),
        )


@dataclass
class PromotionGroup:
    group_id: str | None
    min_purchase_amount: str | None
    discount_type: str | None
    items: list[PromotionItem]

    @classmethod
    def from_xml(
        cls,
        group_element: ET.Element,
        items: list[PromotionItem],
    ) -> "PromotionGroup":
        return cls(
            group_id=optional_text(group_element.findtext("GroupID")),
            min_purchase_amount=optional_text(
                group_element.findtext("MinPurchaseAmount")
            ),
            discount_type=optional_text(group_element.findtext("DiscountType")),
            items=items,
        )


@dataclass
class Promotion:
    chain_id: str | None
    sub_chain_id: str | None
    store_id: str | None
    bikoret_no: str | None
    source_file: str
    extraction_date: str
    promotion_id: str | None
    promotion_description: str | None
    promotion_start_date_time: str | None
    promotion_end_date_time: str | None
    promotion_start_hour: str | None
    promotion_end_hour: str | None
    promotion_update_time: str | None
    allow_multiple_discounts: str | None
    club_id: str | None
    min_no_of_item_offered: str | None
    redemption_limit: str | None
    is_gift_item: str | None
    additional_is_coupon: str | None
    additional_restrictions: str | None
    remarks: str | None
    promotion_days: str | None
    groups: list[PromotionGroup]

    @classmethod
    def from_xml(
        cls,
        promotion_element: ET.Element,
        *,
        chain_id: str | None,
        sub_chain_id: str | None,
        store_id: str | None,
        bikoret_no: str | None,
        source_file: str,
        extraction_date: str,
        groups: list[PromotionGroup],
    ) -> "Promotion":
        return cls(
            chain_id=optional_text(chain_id),
            sub_chain_id=optional_text(sub_chain_id),
            store_id=optional_text(store_id),
            bikoret_no=optional_text(bikoret_no),
            source_file=source_file,
            extraction_date=extraction_date,
            promotion_id=optional_text(promotion_element.findtext("PromotionID")),
            promotion_description=optional_text(
                promotion_element.findtext("PromotionDescription")
            ),
            promotion_start_date_time=optional_text(
                promotion_element.findtext("PromotionStartDateTime")
            ),
            promotion_end_date_time=optional_text(
                promotion_element.findtext("PromotionEndDateTime")
            ),
            promotion_start_hour=optional_text(
                promotion_element.findtext("PromotionStartHour")
            ),
            promotion_end_hour=optional_text(
                promotion_element.findtext("PromotionEndHour")
            ),
            promotion_update_time=optional_text(
                promotion_element.findtext("PromotionUpdateTime")
            ),
            allow_multiple_discounts=optional_text(
                promotion_element.findtext("AllowMultipleDiscounts")
            ),
            club_id=optional_text(promotion_element.findtext("ClubID")),
            min_no_of_item_offered=optional_text(
                promotion_element.findtext("MinNoOfItemOffered")
            ),
            redemption_limit=optional_text(
                promotion_element.findtext("RedemptionLimit")
            ),
            is_gift_item=optional_text(promotion_element.findtext("IsGiftItem")),
            additional_is_coupon=optional_text(
                promotion_element.findtext("AdditionalIsCoupon")
            ),
            additional_restrictions=optional_text(
                promotion_element.findtext("AdditionalRestrictions")
            ),
            remarks=optional_text(promotion_element.findtext("Remarks")),
            promotion_days=optional_text(promotion_element.findtext("PromotionDays")),
            groups=groups,
        )
