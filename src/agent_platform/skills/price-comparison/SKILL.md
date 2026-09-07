---
name: price-comparison
description: Answer "where is this product cheapest" for a specific product the user names, by resolving the name to a barcode and comparing chain prices. Load this when the question is about one product or a short list of products.
license: MIT
compatibility: Requires the find_products and compare_product_prices tools.
---

# Comparing a single product across chains

Use this when the user asks about a specific product: "where is Tnuva milk
cheapest", "how much is this barcode in each chain", "is X cheaper at Victory".

## Procedure

**1. Resolve the name to a barcode.** Unless the user already gave a numeric
`item_code`, call `find_products` with the product name. Names are stored in
Hebrew, so translate an English product name first.

**2. Pick the right match.** `find_products` returns an `is_comparable` flag.
Only comparable products have cross-chain prices. If several matches look
plausible, prefer a comparable one, and if the choice is genuinely ambiguous,
list the candidates with their barcodes and ask which one they meant rather
than guessing.

**3. Compare.** Call `compare_product_prices` with the chosen `item_code`.

**4. Report.** Give each chain's price, name the cheapest chain, and state the
saving in both shekels and percent. Say explicitly when a chain does not
stock the product; a NULL price is missing data, not a price of zero.

## Handling ties

`cheapest_chains` can contain more than one chain. When it does, say the
chains are tied at that price. Do not pick one arbitrarily.

## What to avoid

Do not answer from the product name alone. A product only has a comparable
price if it is in `grocery.price_comparison`.

Do not extrapolate from one product to a chain-wide claim. "Rami Levy is
cheaper for this item" does not mean "Rami Levy is cheaper". For that
question use the `chain-competitiveness` skill.

Do not present a median chain price as the price at a particular branch.

## Example shape of a good answer

> Tnuva 3% milk 1L (barcode 7290000000000) costs 6.90 at Rami Levy, 7.50 at
> Shufersal and 7.90 at Victory. Rami Levy is cheapest, saving 1.00 shekel
> against Victory, about 12.7%.
