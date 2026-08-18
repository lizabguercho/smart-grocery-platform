from collections.abc import Sequence
from pathlib import Path

from src.data_extraction.models import Store
from src.data_extraction.store_parser import parse_store_files
from src.etl.protocols import Parser


class StoresParser(Parser[Store]):
    def parse(self, files: list[Path]) -> Sequence[Store]:
        return parse_store_files(files)
