"""Results returned by the grocery tools.

These are dataclasses rather than dicts: they are internal records the process
already trusts, and pydantic-ai serializes them for the model. Every container
record carries the question it answers alongside the numbers, so the model
never has to guess what a bare list meant.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PERCENT_PRECISION = 1
PRICE_PRECISION = 2

NO_CLASSIFICATION_DATA_NOTE = (
    "grocery.product_classification is empty, so no category-level answer is "
    "possible yet. Product categorization is still in progress; say so instead "
    "of inferring categories from product names."
)
CLASSIFICATION_AVAILABLE_NOTE = (
    "Category labels come from grocery.product_classification and cover only "
    "part of the comparable set."
)


def percent(part: float, whole: float) -> float:
    """Return `part` as a percentage of `whole`, or 0.0 when `whole` is zero."""

    if not whole:
        return 0.0
    return round(part / whole * 100, PERCENT_PRECISION)


@dataclass(frozen=True)
class ProductMatch:
    """A product found by name search."""

    item_code: int
    item_name: str
    manufacturer: str | None
    is_comparable: bool


@dataclass(frozen=True)
class ProductSearchResult:
    """Products whose name matches a search term."""

    query: str
    match_count: int
    matches: list[ProductMatch] = field(default_factory=list)


@dataclass(frozen=True)
class ChainPrice:
    """One chain's price for a product, or None where the chain lacks it."""

    chain: str
    price: float | None


@dataclass(frozen=True)
class ProductPriceComparison:
    """Cross-chain prices for a single product."""

    item_code: int
    item_name: str | None
    manufacturer: str | None
    prices: list[ChainPrice]
    cheapest_chains: list[str]
    cheapest_price: float
    most_expensive_price: float
    absolute_saving: float
    percent_saving: float
    available_chain_count: int


@dataclass(frozen=True)
class ChainWinCount:
    """How often one chain has the lowest price."""

    chain: str
    outright_wins: int
    best_or_tied: int
    outright_win_share_percent: float


@dataclass(frozen=True)
class CheapestChainSummary:
    """How often each chain is cheapest across the comparable set.

    `outright_wins` counts products where the chain is strictly cheaper than
    every other chain stocking it. `best_or_tied` also counts ties, so the
    `best_or_tied` figures sum to more than `products_considered`.
    """

    products_considered: int
    minimum_chains: int
    chains: list[ChainWinCount]
    tied_products: int
    tied_share_percent: float


@dataclass(frozen=True)
class CategoryPriceRow:
    """Per-category competitiveness for one category."""

    category: str
    products: int
    chain_best_or_tied: dict[str, int]
    average_cheapest_price: float | None


@dataclass(frozen=True)
class CategoryPriceSummary:
    """Category-level price competitiveness, with its data caveat attached."""

    classified_products: int
    requested_category: str | None
    note: str
    rows: list[CategoryPriceRow] = field(default_factory=list)


@dataclass(frozen=True)
class DatabaseOverview:
    """What the analytical layer currently holds."""

    products: int
    comparable_products: int
    products_in_all_three_chains: int
    classified_products: int
    stores: int
    chains: list[str]
    available_categories: list[str]
    note: str
