"""Tests for the grocery SQL tools, against a fake database."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic_ai import ModelRetry

from src.agent_platform.grocery.deps import AgentDeps
from src.agent_platform.grocery.grocery_toolset import (
    MAX_SEARCH_LIMIT,
    build_grocery_toolset,
)
from src.agent_platform.grocery.records import NO_CLASSIFICATION_DATA_NOTE
from test.unit.conftest import FakeGroceryDatabase, StubRunContext

# Each fragment appears in exactly one statement in queries.py.
FIND_PRODUCTS = "grocery.products AS p"
COMPARE_PRICES = "worst_price"
CHEAPEST_SUMMARY = "counted"
CATEGORY_SUMMARY = "product_classification AS pcl"
OVERVIEW = "products_in_all_three_chains"
CATEGORIES = "SELECT DISTINCT category"


@pytest.fixture
def toolset():
    return build_grocery_toolset()


def call(toolset, name: str, database: FakeGroceryDatabase, **kwargs):
    """Invoke a tool's underlying function with a stub run context."""

    function = toolset.tools[name].function
    return function(StubRunContext(deps=AgentDeps(database=database)), **kwargs)


@pytest.mark.anyio
async def test_find_products_searches_with_a_wildcard_pattern(toolset) -> None:
    database = FakeGroceryDatabase(
        rows={FIND_PRODUCTS: [(7290001, "חלב 3%", "תנובה", True)]}
    )

    result = await call(toolset, "find_products", database, name_query="חלב")

    assert result.match_count == 1
    assert result.matches[0].item_code == 7290001
    assert result.matches[0].is_comparable is True
    assert database.params_for(FIND_PRODUCTS)[0] == "%חלב%"


@pytest.mark.anyio
async def test_find_products_trims_the_search_term(toolset) -> None:
    database = FakeGroceryDatabase(rows={FIND_PRODUCTS: []})

    await call(toolset, "find_products", database, name_query="  milk  ")

    assert database.params_for(FIND_PRODUCTS)[0] == "%milk%"


@pytest.mark.anyio
async def test_find_products_caps_the_limit(toolset) -> None:
    database = FakeGroceryDatabase(rows={FIND_PRODUCTS: []})

    await call(toolset, "find_products", database, name_query="milk", limit=10_000)

    assert database.params_for(FIND_PRODUCTS)[1] == MAX_SEARCH_LIMIT


@pytest.mark.anyio
async def test_find_products_asks_the_model_again_on_an_empty_term(toolset) -> None:
    database = FakeGroceryDatabase()

    with pytest.raises(ModelRetry):
        await call(toolset, "find_products", database, name_query="   ")


@pytest.mark.anyio
async def test_compare_prices_reports_the_cheapest_chain_and_saving(toolset) -> None:
    database = FakeGroceryDatabase(
        rows={
            COMPARE_PRICES: [
                (
                    7290001,
                    "חלב 3%",
                    "תנובה",
                    Decimal("7.50"),
                    Decimal("6.90"),
                    Decimal("7.90"),
                    Decimal("6.90"),
                    Decimal("7.90"),
                )
            ]
        }
    )

    result = await call(toolset, "compare_product_prices", database, item_code=7290001)

    assert result.cheapest_chains == ["Rami Levy"]
    assert result.cheapest_price == 6.90
    assert result.absolute_saving == 1.00
    assert result.percent_saving == pytest.approx(12.7, abs=0.1)
    assert result.available_chain_count == 3


@pytest.mark.anyio
async def test_compare_prices_reports_every_tied_chain(toolset) -> None:
    database = FakeGroceryDatabase(
        rows={
            COMPARE_PRICES: [
                (
                    7290001,
                    "חלב",
                    None,
                    Decimal("5.00"),
                    Decimal("5.00"),
                    Decimal("6.00"),
                    Decimal("5.00"),
                    Decimal("6.00"),
                )
            ]
        }
    )

    result = await call(toolset, "compare_product_prices", database, item_code=7290001)

    assert result.cheapest_chains == ["Shufersal", "Rami Levy"]


@pytest.mark.anyio
async def test_compare_prices_keeps_a_missing_chain_as_none(toolset) -> None:
    database = FakeGroceryDatabase(
        rows={
            COMPARE_PRICES: [
                (
                    7290001,
                    "חלב",
                    None,
                    Decimal("5.00"),
                    None,
                    Decimal("6.00"),
                    Decimal("5.00"),
                    Decimal("6.00"),
                )
            ]
        }
    )

    result = await call(toolset, "compare_product_prices", database, item_code=7290001)

    prices = {price.chain: price.price for price in result.prices}
    # A chain that does not stock the product must stay None, never become 0.0.
    assert prices["Rami Levy"] is None
    assert result.available_chain_count == 2


@pytest.mark.anyio
async def test_compare_prices_asks_the_model_again_for_an_unknown_product(
    toolset,
) -> None:
    database = FakeGroceryDatabase(rows={})

    with pytest.raises(ModelRetry, match="find_products"):
        await call(toolset, "compare_product_prices", database, item_code=1)


@pytest.mark.anyio
async def test_cheapest_chain_summary_separates_outright_wins_from_ties(
    toolset,
) -> None:
    database = FakeGroceryDatabase(
        rows={CHEAPEST_SUMMARY: [(100, 20, 50, 10, 25, 60, 15, 20)]}
    )

    result = await call(toolset, "cheapest_chain_summary", database)

    assert result.products_considered == 100
    by_chain = {chain.chain: chain for chain in result.chains}
    assert by_chain["Rami Levy"].outright_wins == 50
    assert by_chain["Rami Levy"].best_or_tied == 60
    assert by_chain["Rami Levy"].outright_win_share_percent == 50.0
    assert result.tied_products == 20
    assert result.tied_share_percent == 20.0


@pytest.mark.anyio
async def test_cheapest_chain_summary_defaults_to_two_chains(toolset) -> None:
    database = FakeGroceryDatabase(rows={CHEAPEST_SUMMARY: [(1, 1, 0, 0, 1, 0, 0, 0)]})

    await call(toolset, "cheapest_chain_summary", database)

    assert database.params_for(CHEAPEST_SUMMARY) == (2,)


@pytest.mark.anyio
async def test_cheapest_chain_summary_accepts_all_three_chains(toolset) -> None:
    database = FakeGroceryDatabase(rows={CHEAPEST_SUMMARY: [(1, 1, 0, 0, 1, 0, 0, 0)]})

    await call(toolset, "cheapest_chain_summary", database, minimum_chains=3)

    assert database.params_for(CHEAPEST_SUMMARY) == (3,)


@pytest.mark.anyio
async def test_cheapest_chain_summary_clamps_an_impossible_minimum(toolset) -> None:
    database = FakeGroceryDatabase(rows={CHEAPEST_SUMMARY: [(1, 1, 0, 0, 1, 0, 0, 0)]})

    await call(toolset, "cheapest_chain_summary", database, minimum_chains=9)

    assert database.params_for(CHEAPEST_SUMMARY) == (3,)


@pytest.mark.anyio
async def test_cheapest_chain_summary_handles_an_empty_result(toolset) -> None:
    database = FakeGroceryDatabase(rows={CHEAPEST_SUMMARY: [(0, 0, 0, 0, 0, 0, 0, 0)]})

    result = await call(toolset, "cheapest_chain_summary", database)

    assert result.products_considered == 0
    assert all(chain.outright_win_share_percent == 0.0 for chain in result.chains)


@pytest.mark.anyio
async def test_category_summary_says_so_when_no_categories_exist(toolset) -> None:
    database = FakeGroceryDatabase(rows={CATEGORY_SUMMARY: []})

    result = await call(toolset, "category_price_summary", database)

    assert result.rows == []
    assert result.classified_products == 0
    assert result.note == NO_CLASSIFICATION_DATA_NOTE


@pytest.mark.anyio
async def test_category_summary_reports_per_chain_counts(toolset) -> None:
    database = FakeGroceryDatabase(
        rows={CATEGORY_SUMMARY: [("Dairy & Eggs", 40, 10, 25, 8, Decimal("9.10"))]}
    )

    result = await call(
        toolset, "category_price_summary", database, category="Dairy & Eggs"
    )

    assert result.classified_products == 40
    assert result.rows[0].chain_best_or_tied["Rami Levy"] == 25
    assert result.rows[0].average_cheapest_price == 9.10
    assert result.note != NO_CLASSIFICATION_DATA_NOTE


@pytest.mark.anyio
async def test_category_summary_passes_the_category_as_a_parameter(toolset) -> None:
    database = FakeGroceryDatabase(rows={CATEGORY_SUMMARY: []})

    await call(toolset, "category_price_summary", database, category="Beverages")

    params = database.params_for(CATEGORY_SUMMARY)
    # The category is bound twice: the statement uses it for both the
    # "no filter" check and the equality test.
    assert params[0] == "Beverages"
    assert params[1] == "Beverages"


@pytest.mark.anyio
async def test_overview_reports_counts_and_categories(toolset) -> None:
    database = FakeGroceryDatabase(
        rows={
            OVERVIEW: [(61768, 14816, 6435, 0, 587)],
            CATEGORIES: [("Dairy & Eggs",), ("Snacks",)],
        }
    )

    result = await call(toolset, "database_overview", database)

    assert result.products == 61768
    assert result.comparable_products == 14816
    assert result.products_in_all_three_chains == 6435
    assert result.classified_products == 0
    assert result.available_categories == ["Dairy & Eggs", "Snacks"]
    assert result.chains == ["Shufersal", "Rami Levy", "Victory"]


@pytest.mark.anyio
async def test_every_tool_has_a_description_for_the_model(toolset) -> None:
    for name, tool in toolset.tools.items():
        assert tool.description, f"{name} has no description"


def test_toolset_exposes_only_the_expected_tools(toolset) -> None:
    assert sorted(toolset.tools) == [
        "category_price_summary",
        "cheapest_chain_summary",
        "compare_product_prices",
        "database_overview",
        "find_products",
    ]
