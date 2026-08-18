from pathlib import Path

from src.data_extraction.data_extraction_config import (
    RAMI_LEVY_PRICE_FULL_RAW_DATA_DIR,
    RAMI_LEVY_PROMO_FULL_RAW_DATA_DIR,
    RAMI_LEVY_STORES_RAW_DATA_DIR,
    SHUFERSAL_PRICE_FULL_RAW_DATA_DIR,
    SHUFERSAL_PROMO_FULL_RAW_DATA_DIR,
    SHUFERSAL_STORES_RAW_DATA_DIR,
    VICTORY_PRICE_FULL_RAW_DATA_DIR,
    VICTORY_PROMO_FULL_RAW_DATA_DIR,
    VICTORY_STORES_RAW_DATA_DIR,
)
from src.etl.enums import Chain


def test_raw_directories_use_chain_subfolders() -> None:
    assert (
        SHUFERSAL_PRICE_FULL_RAW_DATA_DIR
        == Path("data/raw/price_full") / Chain.SHUFERSAL
    )
    assert SHUFERSAL_STORES_RAW_DATA_DIR == Path("data/raw/stores") / Chain.SHUFERSAL
    assert (
        SHUFERSAL_PROMO_FULL_RAW_DATA_DIR
        == Path("data/raw/promo_full") / Chain.SHUFERSAL
    )
    assert (
        RAMI_LEVY_PRICE_FULL_RAW_DATA_DIR
        == Path("data/raw/price_full") / Chain.RAMI_LEVY
    )
    assert RAMI_LEVY_STORES_RAW_DATA_DIR == Path("data/raw/stores") / Chain.RAMI_LEVY
    assert (
        RAMI_LEVY_PROMO_FULL_RAW_DATA_DIR
        == Path("data/raw/promo_full") / Chain.RAMI_LEVY
    )
    assert (
        VICTORY_PRICE_FULL_RAW_DATA_DIR == Path("data/raw/price_full") / Chain.VICTORY
    )
    assert VICTORY_STORES_RAW_DATA_DIR == Path("data/raw/stores") / Chain.VICTORY
    assert (
        VICTORY_PROMO_FULL_RAW_DATA_DIR == Path("data/raw/promo_full") / Chain.VICTORY
    )
