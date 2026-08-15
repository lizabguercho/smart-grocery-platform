from src.database_loader.connection import get_connection


def validate_staging() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM grocery.products_staging
                WHERE item_code IS NULL
                   OR store_id IS NULL
                   OR extraction_date IS NULL
                   OR item_price IS NULL;
                """
            )

            invalid_rows = cur.fetchone()[0]

            if invalid_rows > 0:
                raise ValueError(
                    f"Staging validation failed: {invalid_rows} invalid rows found."
                )

            print("Staging validation passed.")
            
def validate_product_prices() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM grocery.product_prices pp
                LEFT JOIN grocery.products p
                    ON pp.item_code = p.item_code
                WHERE p.item_code IS NULL;
                """
            )

            orphan_prices = cur.fetchone()[0]

            if orphan_prices > 0:
                raise ValueError(
                    f"Final validation failed: {orphan_prices} prices "
                    "have no matching product."
                )

            print("Product prices validation passed.")