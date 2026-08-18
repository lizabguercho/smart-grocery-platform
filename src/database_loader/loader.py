from src.data_extraction.models import PriceFullProduct, Promotion, Store
from src.database_loader.connection import get_connection


def load_products_to_staging(products: list[PriceFullProduct]) -> None:
    with get_connection() as conn, conn.cursor() as cur:
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
            rows,
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
    with get_connection() as conn, conn.cursor() as cur:
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
    with get_connection() as conn, conn.cursor() as cur:
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


def load_stores(stores: list[Store]) -> None:
    rows = [
        (
            store.chain_id,
            store.store_id,
            store.chain_name,
            store.sub_chain_id,
            store.sub_chain_name,
            store.bikoret_no,
            store.store_type,
            store.store_name,
            store.address,
            store.city,
            store.zip_code,
            store.source_file,
            store.extraction_date,
        )
        for store in stores
        if store.chain_id is not None and store.store_id is not None
    ]
    skipped = len(stores) - len(rows)
    if skipped:
        print(f"Skipped {skipped} store(s) missing chain_id or store_id.", flush=True)

    with get_connection() as conn, conn.cursor() as cur:
        cur.executemany(
            """
                INSERT INTO grocery.stores (
                    chain_id,
                    store_id,
                    chain_name,
                    sub_chain_id,
                    sub_chain_name,
                    bikoret_no,
                    store_type,
                    store_name,
                    address,
                    city,
                    zip_code,
                    source_file,
                    extraction_date
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (chain_id, store_id)
                DO UPDATE SET
                    chain_name = EXCLUDED.chain_name,
                    sub_chain_id = EXCLUDED.sub_chain_id,
                    sub_chain_name = EXCLUDED.sub_chain_name,
                    bikoret_no = EXCLUDED.bikoret_no,
                    store_type = EXCLUDED.store_type,
                    store_name = EXCLUDED.store_name,
                    address = EXCLUDED.address,
                    city = EXCLUDED.city,
                    zip_code = EXCLUDED.zip_code,
                    source_file = EXCLUDED.source_file,
                    extraction_date = EXCLUDED.extraction_date;
                """,
            rows,
        )
        cur.execute(
            """
                SELECT COUNT(*)
                FROM grocery.stores;
                """
        )
        row_count = cur.fetchone()[0]
        print(f"Stores table now contains {row_count} stores.")


def load_promotions(promotions: list[Promotion]) -> None:
    promotion_rows = []
    group_rows = []
    item_rows = []
    skipped = 0

    for promotion in promotions:
        if (
            promotion.chain_id is None
            or promotion.store_id is None
            or promotion.promotion_id is None
        ):
            skipped += 1
            continue

        promotion_rows.append(
            (
                promotion.chain_id,
                promotion.store_id,
                promotion.promotion_id,
                promotion.extraction_date,
                promotion.sub_chain_id,
                promotion.bikoret_no,
                promotion.promotion_description,
                promotion.promotion_start_date_time,
                promotion.promotion_end_date_time,
                promotion.promotion_start_hour,
                promotion.promotion_end_hour,
                promotion.promotion_update_time,
                promotion.allow_multiple_discounts,
                promotion.club_id,
                promotion.min_no_of_item_offered,
                promotion.redemption_limit,
                promotion.is_gift_item,
                promotion.additional_is_coupon,
                promotion.additional_restrictions,
                promotion.remarks,
                promotion.promotion_days,
                promotion.source_file,
            )
        )

        for group in promotion.groups:
            if group.group_id is None:
                continue

            group_rows.append(
                (
                    promotion.chain_id,
                    promotion.store_id,
                    promotion.promotion_id,
                    group.group_id,
                    promotion.extraction_date,
                    group.min_purchase_amount,
                    group.discount_type,
                )
            )

            for item in group.items:
                if item.item_code is None:
                    continue

                item_rows.append(
                    (
                        promotion.chain_id,
                        promotion.store_id,
                        promotion.promotion_id,
                        group.group_id,
                        item.item_code,
                        promotion.extraction_date,
                        item.item_type,
                        item.is_weighted,
                        item.reward_type,
                        item.min_qty,
                        item.max_qty,
                        item.discounted_price,
                        item.discounted_price_per_mida,
                        item.discount_rate,
                    )
                )

    if skipped:
        print(
            f"Skipped {skipped} promotion(s) missing chain_id, store_id, or promotion_id.",
            flush=True,
        )

    with get_connection() as conn, conn.cursor() as cur:
        cur.executemany(
            """
                INSERT INTO grocery.promotions (
                    chain_id,
                    store_id,
                    promotion_id,
                    extraction_date,
                    sub_chain_id,
                    bikoret_no,
                    promotion_description,
                    promotion_start_date_time,
                    promotion_end_date_time,
                    promotion_start_hour,
                    promotion_end_hour,
                    promotion_update_time,
                    allow_multiple_discounts,
                    club_id,
                    min_no_of_item_offered,
                    redemption_limit,
                    is_gift_item,
                    additional_is_coupon,
                    additional_restrictions,
                    remarks,
                    promotion_days,
                    source_file
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (chain_id, store_id, promotion_id, extraction_date)
                DO UPDATE SET
                    sub_chain_id = EXCLUDED.sub_chain_id,
                    bikoret_no = EXCLUDED.bikoret_no,
                    promotion_description = EXCLUDED.promotion_description,
                    promotion_start_date_time = EXCLUDED.promotion_start_date_time,
                    promotion_end_date_time = EXCLUDED.promotion_end_date_time,
                    promotion_start_hour = EXCLUDED.promotion_start_hour,
                    promotion_end_hour = EXCLUDED.promotion_end_hour,
                    promotion_update_time = EXCLUDED.promotion_update_time,
                    allow_multiple_discounts = EXCLUDED.allow_multiple_discounts,
                    club_id = EXCLUDED.club_id,
                    min_no_of_item_offered = EXCLUDED.min_no_of_item_offered,
                    redemption_limit = EXCLUDED.redemption_limit,
                    is_gift_item = EXCLUDED.is_gift_item,
                    additional_is_coupon = EXCLUDED.additional_is_coupon,
                    additional_restrictions = EXCLUDED.additional_restrictions,
                    remarks = EXCLUDED.remarks,
                    promotion_days = EXCLUDED.promotion_days,
                    source_file = EXCLUDED.source_file;
                """,
            promotion_rows,
        )
        cur.executemany(
            """
                INSERT INTO grocery.promotion_groups (
                    chain_id,
                    store_id,
                    promotion_id,
                    group_id,
                    extraction_date,
                    min_purchase_amount,
                    discount_type
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (
                    chain_id,
                    store_id,
                    promotion_id,
                    group_id,
                    extraction_date
                )
                DO UPDATE SET
                    min_purchase_amount = EXCLUDED.min_purchase_amount,
                    discount_type = EXCLUDED.discount_type;
                """,
            group_rows,
        )
        cur.executemany(
            """
                INSERT INTO grocery.promotion_items (
                    chain_id,
                    store_id,
                    promotion_id,
                    group_id,
                    item_code,
                    extraction_date,
                    item_type,
                    is_weighted,
                    reward_type,
                    min_qty,
                    max_qty,
                    discounted_price,
                    discounted_price_per_mida,
                    discount_rate
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (
                    chain_id,
                    store_id,
                    promotion_id,
                    group_id,
                    item_code,
                    extraction_date
                )
                DO UPDATE SET
                    item_type = EXCLUDED.item_type,
                    is_weighted = EXCLUDED.is_weighted,
                    reward_type = EXCLUDED.reward_type,
                    min_qty = EXCLUDED.min_qty,
                    max_qty = EXCLUDED.max_qty,
                    discounted_price = EXCLUDED.discounted_price,
                    discounted_price_per_mida = EXCLUDED.discounted_price_per_mida,
                    discount_rate = EXCLUDED.discount_rate;
                """,
            item_rows,
        )
        cur.execute(
            """
                SELECT COUNT(*)
                FROM grocery.promotions;
                """
        )
        row_count = cur.fetchone()[0]
        print(f"Promotions table now contains {row_count} promotions.")


def clear_staging() -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE grocery.products_staging;")

    print("Staging table cleared.")
