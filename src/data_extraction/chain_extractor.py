from abc import abstractmethod
from pathlib import Path

from src.etl.constants import STORES_NOT_IMPLEMENTED_MESSAGE
from src.etl.enums import ExtractType
from src.etl.options import PipelineOptions
from src.etl.protocols import Extractor


class ChainExtractor(Extractor):
    def __init__(
        self,
        extract_type: ExtractType,
        options: PipelineOptions,
    ) -> None:
        self.extract_type = extract_type
        self.options = options

    def extract(self) -> list[Path]:
        if self.extract_type is ExtractType.STORES:
            raise NotImplementedError(STORES_NOT_IMPLEMENTED_MESSAGE)
        return self.extract_price_full()

    @abstractmethod
    def extract_price_full(self) -> list[Path]:
        """Download or locate PriceFull files for this chain."""
