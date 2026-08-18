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
            return self.extract_stores()
        if self.extract_type is ExtractType.PROMO_FULL:
            return self.extract_promo_full()

        return self.extract_price_full()

    @abstractmethod
    def extract_price_full(self) -> list[Path]:
        """Download or locate PriceFull files for this chain."""

    @abstractmethod
    def extract_promo_full(self) -> list[Path]:
        """Download or locate PromoFull files for this chain."""

    def extract_stores(self) -> list[Path]:
        """Download or locate Stores files for this chain."""
        raise NotImplementedError(STORES_NOT_IMPLEMENTED_MESSAGE)
