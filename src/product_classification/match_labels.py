from collections import defaultdict
from collections.abc import Sequence

from src.database_loader.connection import get_connection
from src.product_classification.models import SuperCompareProduct
from src.product_classification.supercompare.config import SuperCompareConfig
from src.product_classification.supercompare.storage import SuperCompareBatchStore


def load_database_products() -> dict[str, str]:
    connection = get_connection()

    query = """
        SELECT
            item_code,
            item_name
        FROM grocery.products;
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    connection.close()

    return {str(row[0]): row[1] for row in rows}


def calculate_match_rate(
    supercompare_products: Sequence[SuperCompareProduct],
    database_products: dict[str, str],
) -> None:
    database_codes = set(database_products.keys())
    supercompare_codes = {product.item_code for product in supercompare_products}
    matched_codes = supercompare_codes & database_codes

    print("SuperCompare products:", len(supercompare_codes))
    print("Matched products:", len(matched_codes))

    if supercompare_codes:
        match_rate = len(matched_codes) / len(supercompare_codes) * 100
        print(f"Match rate: {match_rate:.1f}%")

    print("\nMatch rate by category:")

    products_by_category = defaultdict(list)

    for product in supercompare_products:
        products_by_category[product.main_category].append(product)

    for category, products in sorted(products_by_category.items()):
        codes = {product.item_code for product in products}
        matched = codes & database_codes
        rate = len(matched) / len(codes) * 100 if codes else 0
        print(f"  {category}: {len(matched)}/{len(codes)} ({rate:.1f}%)")

    print("\nMatch rate by subcategory:")

    products_by_subcategory = defaultdict(list)

    for product in supercompare_products:
        label = f"{product.main_category} / {product.subcategory}"
        products_by_subcategory[label].append(product)

    for label, products in sorted(products_by_subcategory.items()):
        codes = {product.item_code for product in products}
        matched = codes & database_codes
        rate = len(matched) / len(codes) * 100 if codes else 0
        print(f"  {label}: {len(matched)}/{len(codes)} ({rate:.1f}%)")


def compare_product_names(
    supercompare_products: Sequence[SuperCompareProduct],
    database_products: dict[str, str],
) -> None:
    matched_products = []

    for product in supercompare_products:
        if product.item_code in database_products:
            matched_products.append(product)

    print(f"\nMatched products: {len(matched_products)}")

    for product in matched_products[:30]:
        database_name = database_products[product.item_code]

        print("\nBarcode:", product.item_code)
        print("Category:     ", product.main_category, "/", product.subcategory)
        print("Our DB:       ", database_name)
        print("SuperCompare: ", product.product_name)


def main() -> None:
    store = SuperCompareBatchStore(SuperCompareConfig())
    supercompare_products = store.load_products()
    database_products = load_database_products()

    calculate_match_rate(supercompare_products, database_products)
    compare_product_names(supercompare_products, database_products)


if __name__ == "__main__":
    main()
