from enum import Enum

class ShufersalPriceCategory(Enum):
    ALL = 0
    PRICES = 1
    PRICES_FULL = 2
    PROMOS = 3
    PROMOS_FULL = 4
    STORES = 5
    
# URL constants for the Shufersal data extraction
SHUFERSAL_BASE_URL = "https://prices.shufersal.co.il"
SHUFERSAL_CATEGORY_URL = f"{SHUFERSAL_BASE_URL}/FileObject/UpdateCategory"
