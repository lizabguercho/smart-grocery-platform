from pathlib import Path

from src.data_extraction.chain_extractor import ChainExtractor
from src.data_extraction.data_extraction_config import RAMI_LEVY_RAW_DATA_DIR
from src.data_extraction.local_files import (
    list_local_price_full_files,
    require_local_files,
)
from src.data_extraction.rami_levy.download import download_price_full_files
from src.etl.constants import (
    FOUND_LOCAL_FILES_MESSAGE,
    SKIPPING_DOWNLOAD_MESSAGE,
    USING_FILES_MESSAGE,
)


class RamiLevyExtractor(ChainExtractor):
    def extract_price_full(self) -> list[Path]:
        if self.options.download:
            downloaded_files = download_price_full_files(
                max_files=self.options.max_files,
            )
            print(
                USING_FILES_MESSAGE.format(count=len(downloaded_files)),
                flush=True,
            )
            return downloaded_files

        print(SKIPPING_DOWNLOAD_MESSAGE, flush=True)
        local_files = list_local_price_full_files(RAMI_LEVY_RAW_DATA_DIR)
        print(
            FOUND_LOCAL_FILES_MESSAGE.format(count=len(local_files)),
            flush=True,
        )
        return require_local_files(local_files, RAMI_LEVY_RAW_DATA_DIR)
