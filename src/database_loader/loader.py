from src.database_loader.connection import get_connection
from src.data_extraction.models import PriceFullProduct


def load_products_to_staging(products: list[PriceFullProduct]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE grocery.products_staging;")
            # Convert all PriceFullProduct objects into tuples
            rows = [
                (
                    product.item_code,
                    product.item_name,
                    product.manufacture_name,
                    product.manufacture_country,
                    product.manufacture_item_description,
                    product.unit_qty,
                    product.quantity,
                    product.unit_of_measure,
                    product.is_weighted,
                    product.qty_in_package,
                    product.item_price,
                    product.unit_of_measure_price,
                    product.allow_discount,
                    product.item_status,
                    product.price_update_time,
                    product.last_sale_date_time,
                    product.item_type,
                    product.store_id,
                    product.chain_id,
                    product.sub_chain_id,
                    product.source_file,
                    product.extraction_date,
                )
                for product in products
            ]
            cur.executemany(
                """
                INSERT INTO grocery.products_staging (
                    item_code,
                    item_name,
                    manufacture_name,
                    manufacture_country,
                    manufacture_item_description,
                    unit_qty,
                    quantity,
                    unit_of_measure,
                    is_weighted,
                    qty_in_package,
                    item_price,
                    unit_of_measure_price,
                    allow_discount,
                    item_status,
                    price_update_time,
                    last_sale_date_time,
                    item_type,
                    store_id,
                    chain_id,
                    sub_chain_id,
                    source_file,
                    extraction_date
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                );
                """,
                rows
            )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM grocery.products_staging;
                """
            )

            row_count = cur.fetchone()[0]

            print(f"Inserted {row_count} rows into staging.")


def load_products() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO grocery.products (
                    item_code,
                    item_name,
                    manufacture_name,
                    manufacture_country,
                    manufacture_item_description,
                    unit_qty,
                    quantity,
                    unit_of_measure,
                    is_weighted,
                    qty_in_package,
                    item_type
                )
                SELECT DISTINCT ON (item_code)
                    item_code,
                    item_name,
                    manufacture_name,
                    manufacture_country,
                    manufacture_item_description,
                    unit_qty,
                    quantity,
                    unit_of_measure,
                    is_weighted,
                    qty_in_package,
                    item_type
                FROM grocery.products_staging
                WHERE item_code IS NOT NULL
                ORDER BY item_code, extraction_date DESC
                ON CONFLICT (item_code)
                DO UPDATE SET
                    item_name = EXCLUDED.item_name,
                    manufacture_name = EXCLUDED.manufacture_name,
                    manufacture_country = EXCLUDED.manufacture_country,
                    manufacture_item_description = EXCLUDED.manufacture_item_description,
                    unit_qty = EXCLUDED.unit_qty,
                    quantity = EXCLUDED.quantity,
                    unit_of_measure = EXCLUDED.unit_of_measure,
                    is_weighted = EXCLUDED.is_weighted,
                    qty_in_package = EXCLUDED.qty_in_package,
                    item_type = EXCLUDED.item_type;;
                """
            )
            cur.execute(
                """
                SELECT COUNT(*)
                FROM grocery.products;
                """
            )
            row_count = cur.fetchone()[0]
            print(f"Products table now contains {row_count} products.")



def load_product_prices() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO grocery.product_prices (
                    item_code,
                    store_id,
                    item_price,
                    unit_of_measure_price,
                    price_update_time,
                    last_sale_date_time,
                    item_status,
                    allow_discount,
                    chain_id,
                    sub_chain_id,
                    source_file,
                    extraction_date
                )
                SELECT DISTINCT ON (
                    chain_id,
                    store_id,
                    item_code,
                    extraction_date
                )
                    item_code,
                    store_id,
                    item_price,
                    unit_of_measure_price,
                    price_update_time,
                    last_sale_date_time,
                    item_status,
                    allow_discount,
                    chain_id,
                    sub_chain_id,
                    source_file,
                    extraction_date
                FROM grocery.products_staging
                WHERE item_code IS NOT NULL
                  AND store_id IS NOT NULL
                  AND chain_id IS NOT NULL
                  AND extraction_date IS NOT NULL
                ORDER BY
                    chain_id,
                    store_id,
                    item_code,
                    extraction_date,
                    source_file DESC
                ON CONFLICT (
                    chain_id,
                    store_id,
                    item_code,
                    extraction_date
                )
                DO UPDATE SET
                    item_price = EXCLUDED.item_price,
                    unit_of_measure_price = EXCLUDED.unit_of_measure_price,
                    price_update_time = EXCLUDED.price_update_time,
                    last_sale_date_time = EXCLUDED.last_sale_date_time,
                    item_status = EXCLUDED.item_status,
                    allow_discount = EXCLUDED.allow_discount,
                    sub_chain_id = EXCLUDED.sub_chain_id,
                    source_file = EXCLUDED.source_file;
                """
            )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM grocery.product_prices;
                """
            )
            row_count = cur.fetchone()[0]
            print(f"Product prices table now contains {row_count} rows.")


def clear_staging() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE grocery.products_staging;"
            )

    print("Staging table cleared.")