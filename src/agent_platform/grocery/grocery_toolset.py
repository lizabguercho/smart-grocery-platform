"""The grocery SQL tools exposed to the agent.

Each tool runs exactly one named statement from `queries.py` and returns a
dataclass. Tool docstrings are the descriptions the model sees, so they say
what the tool answers and when to reach for it.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic_ai import FunctionToolset, ModelRetry, RunContext

from src.agent_platform.errors import DatabaseUnavailableError
from src.agent_platform.grocery import queries
from src.agent_platform.grocery.chains import CHAIN_PROFILES
from src.agent_platform.grocery.deps import AgentDeps
from src.agent_platform.grocery.records import (
    CLASSIFICATION_AVAILABLE_NOTE,
    NO_CLASSIFICATION_DATA_NOTE,
    PRICE_PRECISION,
    CategoryPriceRow,
    CategoryPriceSummary,
    ChainPrice,
    ChainWinCount,
    CheapestChainSummary,
    DatabaseOverview,
    ProductMatch,
    ProductPriceComparison,
    ProductSearchResult,
    percent,
)

DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50
DEFAULT_CATEGORY_LIMIT = 20
MIN_CHAINS_FOR_COMPARISON = 2
MAX_CHAINS = 3

SEARCH_PATTERN_TEMPLATE = "%{term}%"
UNKNOWN_PRODUCT_MESSAGE = (
    "Item code {item_code} is not in grocery.price_comparison. Only products "
    "sold by at least two chains are comparable. Call find_products to get a "
    "valid item_code, and tell the user if the product is not comparable."
)
EMPTY_SEARCH_MESSAGE = (
    "name_query was empty. Pass the product name to search for, in Hebrew."
)
OVERVIEW_UNAVAILABLE_MESSAGE = "The analytical layer returned no overview row."
OVERVIEW_NOTE = (
    "Comparable products are those sold by at least two chains, matched on "
    "item_code (barcode). Prices are per-chain medians across that chain's "
    "stores, not a single store's shelf price."
)


def _to_float(value: Decimal | float | None) -> float | None:
    """Convert a numeric column to a float for the model, keeping None as None."""

    if value is None:
        return None
    return round(float(value), PRICE_PRECISION)


def build_grocery_toolset() -> FunctionToolset[AgentDeps]:
    """Build the read-only SQL toolset over the grocery analytical layer."""

    toolset = FunctionToolset[AgentDeps]()

    @toolset.tool
    async def find_products(
        ctx: RunContext[AgentDeps], name_query: str, limit: int = DEFAULT_SEARCH_LIMIT
    ) -> ProductSearchResult:
        """Search products by name and get their item_code (barcode).

        Use this first whenever the user names a product instead of giving a
        barcode. Product names are stored in Hebrew, so pass the Hebrew term
        when the user writes in Hebrew. Results that are comparable across
        chains are listed first.
        """

        term = name_query.strip()
        if not term:
            raise ModelRetry(EMPTY_SEARCH_MESSAGE)
        capped = max(1, min(limit, MAX_SEARCH_LIMIT))
        rows = await ctx.deps.database.fetch_all(
            queries.FIND_PRODUCTS_SQL,
            (SEARCH_PATTERN_TEMPLATE.format(term=term), capped),
        )
        matches = [
            ProductMatch(
                item_code=row[0],
                item_name=row[1],
                manufacturer=row[2],
                is_comparable=row[3],
            )
            for row in rows
        ]
        return ProductSearchResult(
            query=term, match_count=len(matches), matches=matches
        )

    @toolset.tool
    async def compare_product_prices(
        ctx: RunContext[AgentDeps], item_code: int
    ) -> ProductPriceComparison:
        """Compare one product's price across Shufersal, Rami Levy and Victory.

        Takes an item_code (barcode) from find_products. Reports each chain's
        price, which chain or chains are cheapest, and how much is saved by
        buying at the cheapest rather than the most expensive chain.
        """

        row = await ctx.deps.database.fetch_one(
            queries.COMPARE_PRODUCT_PRICES_SQL, (item_code,)
        )
        # A missing product is the model passing a bad argument, not a broken
        # database, so it is handed back as a retry the model can recover from
        # rather than an error that ends the run.
        if row is None:
            raise ModelRetry(UNKNOWN_PRODUCT_MESSAGE.format(item_code=item_code))

        item_name, manufacturer = row[1], row[2]
        raw_prices = {
            profile.chain: row[3 + index]
            for index, profile in enumerate(CHAIN_PROFILES)
        }
        best_price = _to_float(row[6])
        worst_price = _to_float(row[7])
        if best_price is None or worst_price is None:
            raise ModelRetry(UNKNOWN_PRODUCT_MESSAGE.format(item_code=item_code))

        prices = [
            ChainPrice(
                chain=profile.display_name,
                price=_to_float(raw_prices[profile.chain]),
            )
            for profile in CHAIN_PROFILES
        ]
        cheapest_chains = [price.chain for price in prices if price.price == best_price]
        available = [price for price in prices if price.price is not None]
        saving = round(worst_price - best_price, PRICE_PRECISION)

        return ProductPriceComparison(
            item_code=row[0],
            item_name=item_name,
            manufacturer=manufacturer,
            prices=prices,
            cheapest_chains=cheapest_chains,
            cheapest_price=best_price,
            most_expensive_price=worst_price,
            absolute_saving=saving,
            percent_saving=percent(saving, worst_price),
            available_chain_count=len(available),
        )

    @toolset.tool
    async def cheapest_chain_summary(
        ctx: RunContext[AgentDeps], minimum_chains: int = MIN_CHAINS_FOR_COMPARISON
    ) -> CheapestChainSummary:
        """Count how often each chain has the lowest price overall.

        Answers "which supermarket is cheapest most often". Ties are reported
        separately rather than being awarded to one chain. Pass
        minimum_chains=3 to restrict the answer to products stocked by all
        three chains, which removes availability bias.
        """

        floor = max(MIN_CHAINS_FOR_COMPARISON, min(minimum_chains, MAX_CHAINS))
        row = await ctx.deps.database.fetch_one(
            queries.CHEAPEST_CHAIN_SUMMARY_SQL, (floor,)
        )
        if row is None:
            raise DatabaseUnavailableError(OVERVIEW_UNAVAILABLE_MESSAGE)

        products = row[0]
        chains = [
            ChainWinCount(
                chain=profile.display_name,
                outright_wins=row[1 + index],
                best_or_tied=row[4 + index],
                outright_win_share_percent=percent(row[1 + index], products),
            )
            for index, profile in enumerate(CHAIN_PROFILES)
        ]
        return CheapestChainSummary(
            products_considered=products,
            minimum_chains=floor,
            chains=chains,
            tied_products=row[7],
            tied_share_percent=percent(row[7], products),
        )

    @toolset.tool
    async def category_price_summary(
        ctx: RunContext[AgentDeps], category: str | None = None
    ) -> CategoryPriceSummary:
        """Compare chain competitiveness within product categories.

        Answers "which chain is cheapest for dairy / snacks / beverages".
        Pass a category name to focus on one, or omit it for every category.
        Category labels are still being populated, so check the returned note
        before drawing conclusions.
        """

        rows = await ctx.deps.database.fetch_all(
            queries.CATEGORY_PRICE_SUMMARY_SQL,
            (category, category, DEFAULT_CATEGORY_LIMIT),
        )
        summary_rows = [
            CategoryPriceRow(
                category=row[0],
                products=row[1],
                chain_best_or_tied={
                    profile.display_name: row[2 + index]
                    for index, profile in enumerate(CHAIN_PROFILES)
                },
                average_cheapest_price=_to_float(row[5]),
            )
            for row in rows
        ]
        classified = sum(row.products for row in summary_rows)
        return CategoryPriceSummary(
            classified_products=classified,
            requested_category=category,
            note=(
                CLASSIFICATION_AVAILABLE_NOTE
                if summary_rows
                else NO_CLASSIFICATION_DATA_NOTE
            ),
            rows=summary_rows,
        )

    @toolset.tool
    async def database_overview(ctx: RunContext[AgentDeps]) -> DatabaseOverview:
        """Report what the analytical layer currently contains.

        Use this to orient before answering a broad question, to check whether
        category data exists, or to state how many products a conclusion rests
        on.
        """

        row = await ctx.deps.database.fetch_one(queries.DATABASE_OVERVIEW_SQL)
        if row is None:
            raise DatabaseUnavailableError(OVERVIEW_UNAVAILABLE_MESSAGE)
        category_rows = await ctx.deps.database.fetch_all(
            queries.AVAILABLE_CATEGORIES_SQL
        )
        return DatabaseOverview(
            products=row[0],
            comparable_products=row[1],
            products_in_all_three_chains=row[2],
            classified_products=row[3],
            stores=row[4],
            chains=[profile.display_name for profile in CHAIN_PROFILES],
            available_categories=[category_row[0] for category_row in category_rows],
            note=OVERVIEW_NOTE,
        )

    return toolset
