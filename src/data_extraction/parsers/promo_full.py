from collections.abc import Sequence
from pathlib import Path

from src.data_extraction.models import Promotion
from src.data_extraction.promotion_parser import parse_promo_full_files
from src.etl.protocols import Parser


class PromoFullParser(Parser[Promotion]):
    def parse(self, files: list[Path]) -> Sequence[Promotion]:
        return parse_promo_full_files(files)
