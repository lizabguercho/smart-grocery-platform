from collections.abc import Sequence
from typing import Generic

from src.etl.constants import (
    EXTRACT_STEP_MESSAGE,
    EXTRACTED_FILES_MESSAGE,
    LOAD_STEP_MESSAGE,
    PARSE_STEP_MESSAGE,
    PARSED_RECORDS_MESSAGE,
)
from src.etl.protocols import Extractor, Loader, Parser, T


class Pipeline(Generic[T]):
    def __init__(
        self,
        extractor: Extractor,
        parser: Parser[T],
        loader: Loader[T],
    ) -> None:
        self.extractor = extractor
        self.parser = parser
        self.loader = loader

    def run(self) -> Sequence[T]:
        print(EXTRACT_STEP_MESSAGE, flush=True)
        files = self.extractor.extract()
        print(EXTRACTED_FILES_MESSAGE.format(count=len(files)), flush=True)

        print(PARSE_STEP_MESSAGE, flush=True)
        records = self.parser.parse(files)
        print(PARSED_RECORDS_MESSAGE.format(count=len(records)), flush=True)

        print(LOAD_STEP_MESSAGE, flush=True)
        self.loader.load(records)
        return records
