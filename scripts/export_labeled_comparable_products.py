"""Export comparable products joined to SuperCompare category labels as CSV."""

from __future__ import annotations

from src.database_loader.connection import get_remote_connection
from src.product_classification.comparable_labels import (
    DEFAULT_ANALYSIS_CSV_PATH,
    DEFAULT_COMBINED_CSV_PATH,
    ComparableProduct,
    load_unique_products,
    write_combined_csv,
)
from src.product_classification.supercompare.config import DEFAULT_PRODUCTS_PATH


def fetch_comparable_products_and_names() -> tuple[
    list[ComparableProduct],
    dict[str, str],
]:
    print("Loading grocery.price_comparison from the remote database...", flush=True)
    connection = get_remote_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                pc.item_code,
                pc.shufersal_price,
                pc.rami_levy_price,
                pc.victory_price,
                pc.cheapest_price,
                pc.cheapest_chain,
                p.item_name
            FROM grocery.price_comparison AS pc
            LEFT JOIN grocery.products AS p
                ON p.item_code = pc.item_code
            ORDER BY pc.item_code
            """
        )
        rows = cursor.fetchall()
    connection.close()

    comparable_products: list[ComparableProduct] = []
    names: dict[str, str] = {}
    for row in rows:
        item_code = str(row[0])
        comparable_products.append(
            ComparableProduct(
                item_code=item_code,
                shufersal_price=row[1],
                rami_levy_price=row[2],
                victory_price=row[3],
                cheapest_price=row[4],
                cheapest_chain=row[5],
            )
        )
        if row[6] is not None:
            names[item_code] = row[6]
    print(f"Loaded {len(comparable_products)} comparable products", flush=True)
    return comparable_products, names


def main() -> None:
    print("Reading SuperCompare CSV...", flush=True)
    unique_products, dropped = load_unique_products(DEFAULT_PRODUCTS_PATH)
    print(
        f"Unique SuperCompare barcodes: {len(unique_products)} "
        f"(dropped {dropped} duplicate rows)",
        flush=True,
    )
    comparable_products, names = fetch_comparable_products_and_names()
    labels = {product.item_code: product for product in unique_products}
    labeled = sum(1 for product in comparable_products if product.item_code in labels)
    written = write_combined_csv(
        comparable_products,
        labels,
        names,
        DEFAULT_COMBINED_CSV_PATH,
    )
    analysis_rows = write_combined_csv(
        comparable_products,
        labels,
        names,
        DEFAULT_ANALYSIS_CSV_PATH,
        require_label=True,
    )
    print(f"Comparable products written: {written}", flush=True)
    print(f"With SuperCompare category: {labeled}", flush=True)
    print(f"Without SuperCompare category: {written - labeled}", flush=True)
    print(f"Saved {DEFAULT_COMBINED_CSV_PATH}", flush=True)
    print(
        f"Analysis table (price_comparison ∩ SuperCompare): {analysis_rows}",
        flush=True,
    )
    print(f"Saved {DEFAULT_ANALYSIS_CSV_PATH}", flush=True)


if __name__ == "__main__":
    main()
