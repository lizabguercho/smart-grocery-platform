# Table reference

The tools read the `grocery` schema of the shared analytical database. This is
the lightweight analytical copy, not the full local ETL database, so raw
per-store price history and promotions are not reachable from chat.

## grocery.price_comparison

One row per comparable product: a barcode stocked by at least two chains.

| Column | Meaning |
|---|---|
| `item_code` | Barcode, the product key |
| `shufersal_price` | Median Shufersal price, NULL if not stocked |
| `rami_levy_price` | Median Rami Levy price, NULL if not stocked |
| `victory_price` | Median Victory price, NULL if not stocked |
| `cheapest_price` | Lowest of the available prices |
| `cheapest_chain` | Display label, see the warning below |

`cheapest_chain` is a human-readable label that folds ties into strings such
as `Shufersal & Rami Levy` and `All three`. It has seven possible values, not
three. The tools therefore derive the cheapest chain from the price columns
themselves and report ties explicitly, which is why `cheapest_chain_summary`
separates outright wins from ties.

## grocery.products

Product metadata for every barcode seen by the ETL pipeline, including
products that are not comparable.

| Column | Meaning |
|---|---|
| `item_code` | Barcode |
| `item_name` | Product name, in Hebrew |
| `manufacture_name` | Manufacturer |
| `quantity`, `unit_of_measure`, `is_weighted` | Packaging details |

There are far more products here than comparable products, because most
barcodes appear in only one chain.

## grocery.product_classification

Category labels, one row per product. May be empty while categorization is in
progress.

| Column | Meaning |
|---|---|
| `item_code` | Barcode |
| `category` | Main category, for example Dairy & Eggs |
| `subcategory` | Finer category |
| `include_in_analysis` | Whether the label is trusted for analysis |

Only rows with `include_in_analysis` set are used.

## grocery.chain_prices

Median price per `item_code` and `chain_id`, the granular table behind
`price_comparison`. No tool reads it directly; use `compare_product_prices`.

## grocery.stores

Branch reference data: `chain_id`, `store_id`, Hebrew `chain_name`,
`store_name`, `city`. Used only for the store count in `database_overview`.

## Known limitations

Prices are a snapshot, not a time series, so the analytical layer cannot
answer questions about price changes over time.

A product missing from a chain means that barcode was absent from that chain's
published price file, which is not proof the store does not sell it.
