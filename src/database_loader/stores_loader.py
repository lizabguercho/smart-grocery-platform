from collections.abc import Sequence

from src.data_extraction.models import Store
from src.etl.constants import STORES_NOT_IMPLEMENTED_MESSAGE
from src.etl.protocols import Loader


class StoresLoader(Loader[Store]):
    def load(self, records: Sequence[Store]) -> None:
        raise NotImplementedError(STORES_NOT_IMPLEMENTED_MESSAGE)
