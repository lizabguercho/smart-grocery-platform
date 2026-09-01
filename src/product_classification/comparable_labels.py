"""Join SuperCompare silver labels to comparable products and promote them."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from src.product_classification.models import SuperCompareProduct

CLASSIFICATION_METHOD = "supercompare_silver"

# Weak SuperCompare *coverage* (Eggs, produce, beef, spices) is not the same
# as a wrong label. Those slices stay in analysis when the name matches.
# include_in_analysis is False for barcodes whose names do not match the
# SuperCompare class (see data/processed/incorrect_category_labels.csv).
EXCLUDED_ITEM_CODES = frozenset(
    {
        "52070082",
        "72991374",
        "72991381",
        "50000032648",
        "50000426447",
        "5000219009295",
        "5208049015312",
        "5208049015329",
        "5208049015343",
        "5601217129420",
        "7290000302027",
        "7290013083999",
        "7290013268938",
        "7290016509304",
        "7290108352146",
        "7290108352153",
        "7290109924137",
        "7290113302358",
        "7290115190229",
        "7290119372607",
        "8690784616775",
        "8697530910743",
        "8697530910750",
        "8697530910781",
        "8697530911276",
    }
)

STATUS_HIGH = 80.0
STATUS_MEDIUM = 60.0


@dataclass(frozen=True)
class CoverageRow:
    main_category: str
    subcategory: str
    supercompare_unique: int
    matched_comparable: int
    coverage_percent: float
    status: str


@dataclass(frozen=True)
class ClassificationRow:
    item_code: int
    category: str
    subcategory: str
    include_in_analysis: bool
    classification_method: str
    classification_confidence: float | None


def coverage_status(coverage_percent: float) -> str:
    if coverage_percent >= STATUS_HIGH:
        return "high"
    if coverage_percent >= STATUS_MEDIUM:
        return "medium"
    return "low"


def include_in_analysis(item_code: str, subcategory: str | None = None) -> bool:
    del subcategory
    return str(item_code) not in EXCLUDED_ITEM_CODES


def deduplicate_products(
    products: Sequence[SuperCompareProduct],
) -> tuple[list[SuperCompareProduct], int]:
    """Keep the first row per barcode. Conflicts are not expected."""

    by_code: dict[str, SuperCompareProduct] = {}
    for product in products:
        if product.item_code not in by_code:
            by_code[product.item_code] = product
    return list(by_code.values()), len(products) - len(by_code)


def join_to_comparable(
    products: Sequence[SuperCompareProduct],
    comparable_item_codes: Iterable[str],
) -> list[SuperCompareProduct]:
    comparable = set(comparable_item_codes)
    return [product for product in products if product.item_code in comparable]


def coverage_rows(
    unique_products: Sequence[SuperCompareProduct],
    matched_products: Sequence[SuperCompareProduct],
) -> list[CoverageRow]:
    unique_by_sub: dict[tuple[str, str], set[str]] = defaultdict(set)
    matched_by_sub: dict[tuple[str, str], set[str]] = defaultdict(set)

    for product in unique_products:
        unique_by_sub[(product.main_category, product.subcategory)].add(
            product.item_code
        )
    for product in matched_products:
        matched_by_sub[(product.main_category, product.subcategory)].add(
            product.item_code
        )

    rows: list[CoverageRow] = []
    for key in sorted(unique_by_sub):
        main_category, subcategory = key
        total = len(unique_by_sub[key])
        matched = len(matched_by_sub.get(key, set()))
        percent = (matched / total * 100) if total else 0.0
        rows.append(
            CoverageRow(
                main_category=main_category,
                subcategory=subcategory,
                supercompare_unique=total,
                matched_comparable=matched,
                coverage_percent=percent,
                status=coverage_status(percent),
            )
        )
    return rows


def category_counts(
    products: Sequence[SuperCompareProduct],
) -> tuple[Counter[str], Counter[str]]:
    main = Counter(product.main_category for product in products)
    sub = Counter(
        f"{product.main_category} / {product.subcategory}" for product in products
    )
    return main, sub


def to_classification_rows(
    matched_products: Sequence[SuperCompareProduct],
) -> list[ClassificationRow]:
    rows: list[ClassificationRow] = []
    for product in matched_products:
        rows.append(
            ClassificationRow(
                item_code=int(product.item_code),
                category=product.main_category,
                subcategory=product.subcategory,
                include_in_analysis=include_in_analysis(product.item_code),
                classification_method=CLASSIFICATION_METHOD,
                classification_confidence=None,
            )
        )
    return rows


def load_unique_products(csv_path: Path) -> tuple[list[SuperCompareProduct], int]:
    products: list[SuperCompareProduct] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            manufacturer = (row.get("manufacturer") or "").strip() or None
            products.append(
                SuperCompareProduct(
                    item_code=str(row["item_code"]).strip(),
                    product_name=row["product_name"],
                    manufacturer=manufacturer,
                    main_category=row["main_category"],
                    subcategory=row["subcategory"],
                    source_url=row["source_url"],
                )
            )
    return deduplicate_products(products)


def format_share(count: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{count / total * 100:.1f}%"


def sample_codes_by_subcategory(
    products: Sequence[SuperCompareProduct],
    subcategory: str,
    limit: int = 8,
) -> list[SuperCompareProduct]:
    return [product for product in products if product.subcategory == subcategory][
        :limit
    ]


COMBINED_CSV_FIELDS = (
    "item_code",
    "item_name",
    "category",
    "subcategory",
    "include_in_analysis",
    "classification_method",
    "shufersal_price",
    "rami_levy_price",
    "victory_price",
    "cheapest_price",
    "cheapest_chain",
    "supercompare_product_name",
    "manufacturer",
    "source_url",
)

DEFAULT_COMBINED_CSV_PATH = Path(
    "data/processed/comparable_products_with_categories.csv"
)
DEFAULT_ANALYSIS_CSV_PATH = Path(
    "data/processed/price_comparison_with_categories.csv"
)


@dataclass(frozen=True)
class ComparableProduct:
    item_code: str
    shufersal_price: object
    rami_levy_price: object
    victory_price: object
    cheapest_price: object
    cheapest_chain: str | None


def write_combined_csv(
    comparable_products: Sequence[ComparableProduct],
    labels: Mapping[str, SuperCompareProduct],
    database_names: Mapping[str, str],
    output_path: Path,
    *,
    require_label: bool = False,
) -> int:
    """Write comparable products joined to SuperCompare labels.

    When ``require_label`` is True, only barcodes present in both
    ``price_comparison`` and SuperCompare are written. That is the
    analysis table for cheapest-chain-by-category work.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMBINED_CSV_FIELDS)
        writer.writeheader()
        for product in comparable_products:
            label = labels.get(product.item_code)
            if require_label and label is None:
                continue
            written += 1
            writer.writerow(
                {
                    "item_code": product.item_code,
                    "item_name": database_names.get(product.item_code, ""),
                    "category": label.main_category if label else "",
                    "subcategory": label.subcategory if label else "",
                    "include_in_analysis": (
                        include_in_analysis(product.item_code) if label else ""
                    ),
                    "classification_method": (
                        CLASSIFICATION_METHOD if label else ""
                    ),
                    "shufersal_price": product.shufersal_price
                    if product.shufersal_price is not None
                    else "",
                    "rami_levy_price": product.rami_levy_price
                    if product.rami_levy_price is not None
                    else "",
                    "victory_price": product.victory_price
                    if product.victory_price is not None
                    else "",
                    "cheapest_price": product.cheapest_price
                    if product.cheapest_price is not None
                    else "",
                    "cheapest_chain": product.cheapest_chain or "",
                    "supercompare_product_name": label.product_name if label else "",
                    "manufacturer": (label.manufacturer or "") if label else "",
                    "source_url": label.source_url if label else "",
                }
            )
    return written


def name_agreement_examples(
    products: Sequence[SuperCompareProduct],
    database_names: Mapping[str, str],
    limit: int = 8,
) -> list[tuple[str, str, str, str, str]]:
    examples: list[tuple[str, str, str, str, str]] = []
    for product in products:
        db_name = database_names.get(product.item_code)
        if db_name is None:
            continue
        examples.append(
            (
                product.item_code,
                product.main_category,
                product.subcategory,
                db_name,
                product.product_name,
            )
        )
        if len(examples) >= limit:
            break
    return examples
