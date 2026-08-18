from collections.abc import Sequence

from src.data_extraction.models import Promotion
from src.database_loader.loader import load_promotions
from src.etl.protocols import Loader


class PromoFullLoader(Loader[Promotion]):
    def load(self, records: Sequence[Promotion]) -> None:
        load_promotions(list(records))
