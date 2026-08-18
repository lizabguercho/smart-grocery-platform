from collections.abc import Sequence

from src.data_extraction.models import PriceFullProduct
from src.database_loader.loader import (
    clear_staging,
    load_product_prices,
    load_products,
    load_products_to_staging,
)
from src.database_loader.validation import validate_product_prices, validate_staging
from src.etl.protocols import Loader


class PriceFullLoader(Loader[PriceFullProduct]):
    def load(self, records: Sequence[PriceFullProduct]) -> None:
        products = list(records)
        load_products_to_staging(products)
        validate_staging()
        load_products()
        load_product_prices()
        validate_product_prices()
        clear_staging()
