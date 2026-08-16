from __future__ import annotations

import pytest

from src.data_extraction.parsers.price_full import PriceFullParser
from src.data_extraction.parsers.stores import StoresParser
from src.data_extraction.rami_levy.extractor import RamiLevyExtractor
from src.data_extraction.shufersal.extractor import ShufersalExtractor
from src.data_extraction.victory.extractor import VictoryExtractor
from src.database_loader.price_full_loader import PriceFullLoader
from src.database_loader.stores_loader import StoresLoader
from src.etl.constants import STORES_NOT_IMPLEMENTED_MESSAGE
from src.etl.enums import Chain, ExtractType
from src.etl.factory import PipelineFactory
from src.etl.options import PipelineOptions

PRICE_FULL_CASES = (
    (Chain.SHUFERSAL, ShufersalExtractor),
    (Chain.RAMI_LEVY, RamiLevyExtractor),
    (Chain.VICTORY, VictoryExtractor),
)


@pytest.mark.parametrize(("chain", "extractor_cls"), PRICE_FULL_CASES)
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


@pytest.mark.parametrize("chain", list(Chain))
def test_factory_stores_pipeline_raises_not_implemented(chain: Chain) -> None:
    pipeline = PipelineFactory.create(
        chain=chain,
        extract_type=ExtractType.STORES,
        options=PipelineOptions(),
    )

    assert isinstance(pipeline.parser, StoresParser)
    assert isinstance(pipeline.loader, StoresLoader)

    with pytest.raises(NotImplementedError, match=STORES_NOT_IMPLEMENTED_MESSAGE):
        pipeline.run()
