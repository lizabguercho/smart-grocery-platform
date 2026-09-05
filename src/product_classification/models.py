from dataclasses import dataclass


@dataclass
class AnalysisProduct:
    item_code: int
    item_name: str
    manufacture_name: str | None
    manufacture_item_description: str | None


@dataclass
class SuperCompareProduct:
    item_code: str
    product_name: str
    manufacturer: str | None
    main_category: str
    subcategory: str
    source_url: str
