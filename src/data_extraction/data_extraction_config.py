from enum import Enum
from pathlib import Path


class ShufersalPriceCategory(Enum):
    ALL = 0
    PRICES = 1
    PRICES_FULL = 2
    PROMOS = 3
    PROMOS_FULL = 4
    STORES = 5


# Shufersal identification
SHUFERSAL_CHAIN_NAME = "shufersal"

# URL constants for the Shufersal data extraction
SHUFERSAL_BASE_URL = "https://prices.shufersal.co.il"
SHUFERSAL_CATEGORY_URL = f"{SHUFERSAL_BASE_URL}/FileObject/UpdateCategory"

# Download settings
RAW_DATA_DIR = Path("data/raw/shufersal")
SKIP_EXISTING_DOWNLOADS = True
PRICE_FULL_FILE_GLOB = "*PriceFull*"
PRICE_FULL_FILE_LABEL = "PriceFull"
PRICE_FULL_FILENAME_PREFIX = "pricefull"
GZIP_EXTENSION = ".gz"
PRICE_FULL_FILENAME_MIN_PARTS = 5
DOWNLOAD_CHUNK_SIZE_BYTES = 8192

# Shufersal HTTP
SHUFERSAL_PAGE_TIMEOUT_SECONDS = 30
SHUFERSAL_DOWNLOAD_TIMEOUT_SECONDS = 60
SHUFERSAL_DEFAULT_STORE_ID = 0
SHUFERSAL_PARAM_CATEGORY_ID = "catID"
SHUFERSAL_PARAM_STORE_ID = "storeId"
SHUFERSAL_PARAM_PAGE = "page"
HTML_PARSER = "html.parser"

# Rami Levy identification / FTP source (Cerberus published prices)
RAMI_LEVY_CHAIN_NAME = "rami_levy"
RAMI_LEVY_RAW_DATA_DIR = Path("data/raw/rami_levy")
RAMI_LEVY_FTP_HOST = "url.retail.publishedprices.co.il"
RAMI_LEVY_FTP_USERNAME = "RamiLevi"
RAMI_LEVY_FTP_PASSWORD = ""
RAMI_LEVY_FTP_TIMEOUT_SECONDS = 60
RAMI_LEVY_FTP_PORT = 21

# Victory identification / HTTP API source (laibcatalog)
VICTORY_CHAIN_NAME = "victory"
VICTORY_RAW_DATA_DIR = Path("data/raw/victory")
VICTORY_BASE_URL = "https://laibcatalog.co.il"
VICTORY_CHAIN_ID = "7290696200003"
VICTORY_FILES_API_PATH = "/webapi/api/getfiles"
VICTORY_DOWNLOAD_PATH_PREFIX = "/webapi"
VICTORY_API_TIMEOUT_SECONDS = 60
VICTORY_DOWNLOAD_TIMEOUT_SECONDS = 120
VICTORY_EDI_PARAM = "edi"
VICTORY_FILE_TYPE_KEY = "fileType"
VICTORY_FILE_DATE_KEY = "fileDate"
VICTORY_FILE_NAME_KEY = "fileName"
VICTORY_BRANCH_NUMBER_KEY = "branchNumber"
VICTORY_PRICE_FULL_FILE_TYPE = "pricefull"
