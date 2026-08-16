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
    """Placeholder store record for the reserved Stores extract type."""

    store_id: str | None = None
    chain_id: str | None = None
    sub_chain_id: str | None = None
    store_name: str | None = None
    address: str | None = None
    city: str | None = None
    zip_code: str | None = None
    source_file: str | None = None
