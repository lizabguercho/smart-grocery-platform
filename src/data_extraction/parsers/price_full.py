from collections.abc import Sequence
from pathlib import Path

from src.data_extraction.models import PriceFullProduct
from src.data_extraction.price_full_parser import parse_price_full_files
from src.etl.protocols import Parser


class PriceFullParser(Parser[PriceFullProduct]):
    def parse(self, files: list[Path]) -> Sequence[PriceFullProduct]:
        return parse_price_full_files(files)
