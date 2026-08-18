from src.data_extraction.models import Promotion
from src.database_loader.loader import load_promotions


def test_load_promotions_upserts_promotion_group_and_item_rows(
    patch_loader_connection,
    promotion: Promotion,
) -> None:
    _, cursor = patch_loader_connection
    cursor.fetchone_value = (1,)

    load_promotions([promotion])

    promotion_sql, promotion_rows = cursor.executed[0]
    group_sql, group_rows = cursor.executed[1]
    item_sql, item_rows = cursor.executed[2]
    count_sql, _ = cursor.executed[3]

    assert "INSERT INTO grocery.promotions" in promotion_sql
    assert "ON CONFLICT (chain_id, store_id, promotion_id, extraction_date)" in (
        promotion_sql
    )
    assert "INSERT INTO grocery.promotion_groups" in group_sql
    assert "ON CONFLICT" in group_sql
    assert "INSERT INTO grocery.promotion_items" in item_sql
    assert "ON CONFLICT" in item_sql
    assert promotion_rows == [
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
    ]
    assert group_rows == [
        (
            promotion.chain_id,
            promotion.store_id,
            promotion.promotion_id,
            promotion.groups[0].group_id,
            promotion.extraction_date,
            promotion.groups[0].min_purchase_amount,
            promotion.groups[0].discount_type,
        )
    ]
    assert item_rows == [
        (
            promotion.chain_id,
            promotion.store_id,
            promotion.promotion_id,
            promotion.groups[0].group_id,
            promotion.groups[0].items[0].item_code,
            promotion.extraction_date,
            promotion.groups[0].items[0].item_type,
            promotion.groups[0].items[0].is_weighted,
            promotion.groups[0].items[0].reward_type,
            promotion.groups[0].items[0].min_qty,
            promotion.groups[0].items[0].max_qty,
            promotion.groups[0].items[0].discounted_price,
            promotion.groups[0].items[0].discounted_price_per_mida,
            promotion.groups[0].items[0].discount_rate,
        )
    ]
    assert "FROM grocery.promotions" in count_sql


def test_load_promotions_skips_rows_missing_keys(
    patch_loader_connection,
    promotion: Promotion,
) -> None:
    _, cursor = patch_loader_connection
    cursor.fetchone_value = (0,)
    incomplete = Promotion(
        chain_id=None,
        sub_chain_id=promotion.sub_chain_id,
        store_id=promotion.store_id,
        bikoret_no=promotion.bikoret_no,
        source_file=promotion.source_file,
        extraction_date=promotion.extraction_date,
        promotion_id=promotion.promotion_id,
        promotion_description=promotion.promotion_description,
        promotion_start_date_time=promotion.promotion_start_date_time,
        promotion_end_date_time=promotion.promotion_end_date_time,
        promotion_start_hour=promotion.promotion_start_hour,
        promotion_end_hour=promotion.promotion_end_hour,
        promotion_update_time=promotion.promotion_update_time,
        allow_multiple_discounts=promotion.allow_multiple_discounts,
        club_id=promotion.club_id,
        min_no_of_item_offered=promotion.min_no_of_item_offered,
        redemption_limit=promotion.redemption_limit,
        is_gift_item=promotion.is_gift_item,
        additional_is_coupon=promotion.additional_is_coupon,
        additional_restrictions=promotion.additional_restrictions,
        remarks=promotion.remarks,
        promotion_days=promotion.promotion_days,
        groups=promotion.groups,
    )

    load_promotions([incomplete])

    promotion_sql, promotion_rows = cursor.executed[0]
    _, group_rows = cursor.executed[1]
    _, item_rows = cursor.executed[2]

    assert "INSERT INTO grocery.promotions" in promotion_sql
    assert promotion_rows == []
    assert group_rows == []
    assert item_rows == []
