from collections.abc import Sequence

from src.data_extraction.models import Store
from src.database_loader.loader import load_stores
from src.etl.protocols import Loader


class StoresLoader(Loader[Store]):
    def load(self, records: Sequence[Store]) -> None:
        load_stores(list(records))
