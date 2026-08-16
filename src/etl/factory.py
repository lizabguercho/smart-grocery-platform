from src.data_extraction.chain_extractor import ChainExtractor
from src.data_extraction.parsers.price_full import PriceFullParser
from src.data_extraction.parsers.stores import StoresParser
from src.data_extraction.rami_levy.extractor import RamiLevyExtractor
from src.data_extraction.shufersal.extractor import ShufersalExtractor
from src.data_extraction.victory.extractor import VictoryExtractor
from src.database_loader.price_full_loader import PriceFullLoader
from src.database_loader.stores_loader import StoresLoader
from src.etl.enums import Chain, ExtractType
from src.etl.options import PipelineOptions
from src.etl.pipeline import Pipeline
from src.etl.protocols import Extractor, Loader, Parser

_EXTRACTORS: dict[Chain, type[ChainExtractor]] = {
    Chain.SHUFERSAL: ShufersalExtractor,
    Chain.RAMI_LEVY: RamiLevyExtractor,
    Chain.VICTORY: VictoryExtractor,
}


class PipelineFactory:
    @staticmethod
    def create(
        chain: Chain,
        extract_type: ExtractType,
        options: PipelineOptions,
    ) -> Pipeline:
        extractor = _build_extractor(chain, extract_type, options)
        parser = _build_parser(extract_type)
        loader = _build_loader(extract_type)
        return Pipeline(extractor, parser, loader)


def _build_extractor(
    chain: Chain,
    extract_type: ExtractType,
    options: PipelineOptions,
) -> Extractor:
    try:
        extractor_cls = _EXTRACTORS[chain]
    except KeyError as error:
        raise ValueError(f"Unsupported chain: {chain}") from error
    return extractor_cls(extract_type, options)


def _build_parser(extract_type: ExtractType) -> Parser:
    if extract_type is ExtractType.PRICES_FULL:
        return PriceFullParser()
    if extract_type is ExtractType.STORES:
        return StoresParser()
    raise ValueError(f"Unsupported extract type: {extract_type}")


def _build_loader(extract_type: ExtractType) -> Loader:
    if extract_type is ExtractType.PRICES_FULL:
        return PriceFullLoader()
    if extract_type is ExtractType.STORES:
        return StoresLoader()
    raise ValueError(f"Unsupported extract type: {extract_type}")
