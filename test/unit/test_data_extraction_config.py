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


def test_raw_directories_use_chain_subfolders() -> None:
    assert SHUFERSAL_PRICE_FULL_RAW_DATA_DIR == Path("data/raw/price_full/shufersal")
    assert SHUFERSAL_STORES_RAW_DATA_DIR == Path("data/raw/stores/shufersal")
    assert SHUFERSAL_PROMO_FULL_RAW_DATA_DIR == Path("data/raw/promo_full/shufersal")
    assert RAMI_LEVY_PRICE_FULL_RAW_DATA_DIR == Path("data/raw/price_full/rami_levy")
    assert RAMI_LEVY_STORES_RAW_DATA_DIR == Path("data/raw/stores/rami_levy")
    assert RAMI_LEVY_PROMO_FULL_RAW_DATA_DIR == Path("data/raw/promo_full/rami_levy")
    assert VICTORY_PRICE_FULL_RAW_DATA_DIR == Path("data/raw/price_full/victory")
    assert VICTORY_STORES_RAW_DATA_DIR == Path("data/raw/stores/victory")
    assert VICTORY_PROMO_FULL_RAW_DATA_DIR == Path("data/raw/promo_full/victory")
