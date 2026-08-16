from enum import Enum


class Chain(str, Enum):
    SHUFERSAL = "shufersal"
    RAMI_LEVY = "rami_levy"
    VICTORY = "victory"


class ExtractType(str, Enum):
    PRICES_FULL = "prices_full"
    STORES = "stores"
