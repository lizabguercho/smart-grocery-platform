---
name: chain-competitiveness
description: Answer "which supermarket is cheapest overall" or "which chain is cheapest for a category", handling ties and availability bias correctly. Load this for chain-wide or category-wide questions rather than single-product ones.
license: MIT
compatibility: Requires the cheapest_chain_summary, category_price_summary and database_overview tools.
---

# Which chain is cheapest

Use this for questions about chains as a whole: "which supermarket is
cheapest", "is Rami Levy really cheaper", "which chain wins on dairy".

## Procedure

**1. Get the overall picture.** Call `cheapest_chain_summary`. By default it
covers every comparable product, meaning products stocked by at least two
chains.

**2. Check availability bias.** Call it again with `minimum_chains=3`. This
restricts the count to products all three chains stock. If the ranking or the
margins shift noticeably between the two runs, that difference is itself the
finding: part of a chain's apparent advantage came from which products it
stocks rather than from its prices.

**3. Go category by category only if asked.** Call `category_price_summary`.
Always read its `note` field first; if categories are not yet populated, say
so plainly and stop, rather than substituting your own categorization.

## Ties are not wins

The summary separates two figures per chain:

- `outright_wins`: the chain is strictly cheaper than every other chain
  stocking the product.
- `best_or_tied`: the chain matches the lowest price, ties included.

`best_or_tied` sums to more than the product total across chains, because a
tie counts for every chain involved. Use `outright_wins` for "wins most
often". Report `tied_products` alongside it; ties are a real share of the
comparable set and hiding them overstates the winner.

## Reporting

Lead with counts and shares, not adjectives: "Rami Levy has the lowest price
outright for N of M comparable products, X%".

Give the runner-up too. A single number without context invites the wrong
conclusion.

Being cheapest most often is not the same as being cheapest by the largest
margin, and neither is the same as being cheapest for a given shopping basket.
If the user's real question is about a basket, say that this tool answers the
per-product question instead.

State the caveats that apply: prices are per-chain medians, comparison is by
exact barcode, and the comparable set is a subset of each chain's catalogue.
