from __future__ import annotations

import pytest

from src.data_extraction.parsers.price_full import PriceFullParser
from src.data_extraction.parsers.promo_full import PromoFullParser
from src.data_extraction.parsers.stores import StoresParser
from src.data_extraction.rami_levy.extractor import RamiLevyExtractor
from src.data_extraction.shufersal.extractor import ShufersalExtractor
from src.data_extraction.victory.extractor import VictoryExtractor
from src.database_loader.price_full_loader import PriceFullLoader
from src.database_loader.promotions_loader import PromoFullLoader
from src.database_loader.stores_loader import StoresLoader
from src.etl.enums import Chain, ExtractType
from src.etl.factory import PipelineFactory
from src.etl.options import PipelineOptions

CHAIN_EXTRACTORS = (
    (Chain.SHUFERSAL, ShufersalExtractor),
    (Chain.RAMI_LEVY, RamiLevyExtractor),
    (Chain.VICTORY, VictoryExtractor),
)


@pytest.mark.parametrize(("chain", "extractor_cls"), CHAIN_EXTRACTORS)
def test_factory_wires_price_full_strategies(
    chain: Chain,
    extractor_cls: type,
) -> None:
    options = PipelineOptions(download=False, max_files=3, max_pages=2)

    pipeline = PipelineFactory.create(
        chain=chain,
        extract_type=ExtractType.PRICES_FULL,
        options=options,
    )

    assert isinstance(pipeline.extractor, extractor_cls)
    assert isinstance(pipeline.parser, PriceFullParser)
    assert isinstance(pipeline.loader, PriceFullLoader)
    assert pipeline.extractor.extract_type is ExtractType.PRICES_FULL
    assert pipeline.extractor.options is options


@pytest.mark.parametrize(("chain", "extractor_cls"), CHAIN_EXTRACTORS)
def test_factory_wires_stores_strategies(
    chain: Chain,
    extractor_cls: type,
) -> None:
    pipeline = PipelineFactory.create(
        chain=chain,
        extract_type=ExtractType.STORES,
        options=PipelineOptions(),
    )

    assert isinstance(pipeline.extractor, extractor_cls)
    assert isinstance(pipeline.parser, StoresParser)
    assert isinstance(pipeline.loader, StoresLoader)
    assert pipeline.extractor.extract_type is ExtractType.STORES


@pytest.mark.parametrize(("chain", "extractor_cls"), CHAIN_EXTRACTORS)
def test_factory_wires_promo_full_strategies(
    chain: Chain,
    extractor_cls: type,
) -> None:
    pipeline = PipelineFactory.create(
        chain=chain,
        extract_type=ExtractType.PROMO_FULL,
        options=PipelineOptions(),
    )

    assert isinstance(pipeline.extractor, extractor_cls)
    assert isinstance(pipeline.parser, PromoFullParser)
    assert isinstance(pipeline.loader, PromoFullLoader)
    assert pipeline.extractor.extract_type is ExtractType.PROMO_FULL
