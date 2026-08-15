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

# Rami Levy identification / FTP source (Cerberus published prices)
RAMI_LEVY_CHAIN_NAME = "rami_levy"
RAMI_LEVY_RAW_DATA_DIR = Path("data/raw/rami_levy")
RAMI_LEVY_FTP_HOST = "url.retail.publishedprices.co.il"
RAMI_LEVY_FTP_USERNAME = "RamiLevi"
RAMI_LEVY_FTP_PASSWORD = ""
RAMI_LEVY_FTP_TIMEOUT_SECONDS = 60

# Victory identification / HTTP API source (laibcatalog)
VICTORY_CHAIN_NAME = "victory"
VICTORY_RAW_DATA_DIR = Path("data/raw/victory")
VICTORY_BASE_URL = "https://laibcatalog.co.il"
VICTORY_CHAIN_ID = "7290696200003"
