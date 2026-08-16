from collections.abc import Sequence
from pathlib import Path

from src.data_extraction.models import Store
from src.etl.constants import STORES_NOT_IMPLEMENTED_MESSAGE
from src.etl.protocols import Parser


class StoresParser(Parser[Store]):
    def parse(self, files: list[Path]) -> Sequence[Store]:
        raise NotImplementedError(STORES_NOT_IMPLEMENTED_MESSAGE)
