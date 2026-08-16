from pathlib import Path

from src.data_extraction.chain_extractor import ChainExtractor
from src.data_extraction.data_extraction_config import RAW_DATA_DIR
from src.data_extraction.local_files import (
    list_local_price_full_files,
    require_local_files,
)
from src.data_extraction.shufersal.download import (
    download_files,
    get_all_price_full_links,
)
from src.etl.constants import (
    FOUND_LINKS_MESSAGE,
    FOUND_LOCAL_FILES_MESSAGE,
    SKIPPING_DOWNLOAD_MESSAGE,
    USING_FILES_MESSAGE,
)


class ShufersalExtractor(ChainExtractor):
    def extract_price_full(self) -> list[Path]:
        if self.options.download:
            links = get_all_price_full_links(max_pages=self.options.max_pages)
            print(FOUND_LINKS_MESSAGE.format(count=len(links)), flush=True)
            downloaded_files = download_files(
                links,
                max_files=self.options.max_files,
            )
            print(
                USING_FILES_MESSAGE.format(count=len(downloaded_files)),
                flush=True,
            )
            return downloaded_files

        print(SKIPPING_DOWNLOAD_MESSAGE, flush=True)
        local_files = list_local_price_full_files(RAW_DATA_DIR)
        print(
            FOUND_LOCAL_FILES_MESSAGE.format(count=len(local_files)),
            flush=True,
        )
        return require_local_files(local_files, RAW_DATA_DIR)
