from pathlib import Path

from src.data_extraction.chain_extractor import ChainExtractor
from src.etl.enums import ExtractType
from src.etl.options import PipelineOptions


class _FakeExtractor(ChainExtractor):
    def extract_price_full(self) -> list[Path]:
        return [Path("price_full.gz")]

    def extract_stores(self) -> list[Path]:
        return [Path("stores.gz")]

    def extract_promo_full(self) -> list[Path]:
        return [Path("promo_full.gz")]


def test_extract_dispatches_promo_full() -> None:
    extractor = _FakeExtractor(ExtractType.PROMO_FULL, PipelineOptions())

    assert extractor.extract() == [Path("promo_full.gz")]


def test_extract_dispatches_stores() -> None:
    extractor = _FakeExtractor(ExtractType.STORES, PipelineOptions())

    assert extractor.extract() == [Path("stores.gz")]


def test_extract_dispatches_price_full() -> None:
    extractor = _FakeExtractor(ExtractType.PRICES_FULL, PipelineOptions())

    assert extractor.extract() == [Path("price_full.gz")]
