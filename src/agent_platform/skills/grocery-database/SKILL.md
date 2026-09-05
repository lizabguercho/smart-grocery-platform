---
name: grocery-database
description: Understand the grocery analytical tables, what each tool reads, and which claims the data can and cannot support. Load this before answering any question about the data itself.
license: MIT
compatibility: Requires the REMOTE_DB_* connection to the shared analytical database.
---

# Grocery analytical database

The chat service reads the shared analytical layer of the Smart Grocery
Platform: grocery prices from three Israeli supermarket chains, Shufersal,
Rami Levy and Victory.

## What you can query

You have five read-only tools. There is no free-form SQL, so if a question
cannot be answered by combining these tools, say so.

| Tool | Answers |
|---|---|
| `find_products` | "What is the item_code for this product name?" |
| `compare_product_prices` | "How much is this product in each chain?" |
| `cheapest_chain_summary` | "Which chain is cheapest most often?" |
| `category_price_summary` | "Which chain is cheapest for dairy / snacks?" |
| `database_overview` | "How much data is there? What categories exist?" |

Read `REFERENCE.md` for the table and column definitions behind these tools.

## Facts that change how you answer

**Products are matched by barcode.** Two products are "comparable" only when
the exact same `item_code` appears in at least two chains. This is an
exact-product comparison, not a similar-product comparison.

**Prices are per-chain medians, not shelf prices.** Each chain price is the
median across that chain's stores. Never present one as the price at a
specific branch.

**Product names are in Hebrew.** Search with the Hebrew term when the user
writes in Hebrew. If the user writes in English, translate the product name
before calling `find_products`.

**Categories are incomplete.** `grocery.product_classification` is being
populated and may be empty. `category_price_summary` returns a `note` field
saying so. Report that limitation rather than guessing categories from
product names.

## How to answer well

State the size of the evidence. "Rami Levy is cheapest for 8,250 of 14,816
comparable products" is a useful answer; "Rami Levy is cheapest" is not.

Prefer the tools' own numbers over arithmetic of your own. If you do compute
something, show which tool figures it came from.

If a tool reports zero rows, say the data is missing. Do not fill the gap
from background knowledge about Israeli supermarkets.
