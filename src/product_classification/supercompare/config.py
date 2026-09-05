from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUPERCOMPARE_BASE_URL = "https://www.supercompare.co.il"
SUPERCOMPARE_USER_AGENT = "Smart-Grocery-Platform research crawler"
DEFAULT_CITY = "tel-aviv"
DEFAULT_PAGE_SIZE = 24

DEFAULT_CONNECT_TIMEOUT_SECONDS = 10.0
DEFAULT_READ_TIMEOUT_SECONDS = 30.0
DEFAULT_REQUEST_INTERVAL_SECONDS = 1.0
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_BACKOFF_INITIAL_SECONDS = 1.0
DEFAULT_BACKOFF_MAX_SECONDS = 30.0
DEFAULT_RETRY_AFTER_MAX_SECONDS = 120.0

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

DEFAULT_RAW_DIR = Path("data/raw/supercompare")
DEFAULT_PRODUCTS_PATH = Path("data/processed/supercompare_products.csv")
DEFAULT_REPORT_PATH = Path("data/processed/supercompare_crawl_report.json")
DEFAULT_LOG_PATH = Path("data/logs/supercompare_crawler.log")

CHECKPOINT_VERSION = 1
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


@dataclass(frozen=True)
class SuperCompareConfig:
    base_url: str = SUPERCOMPARE_BASE_URL
    user_agent: str = SUPERCOMPARE_USER_AGENT
    city: str = DEFAULT_CITY
    page_size: int = DEFAULT_PAGE_SIZE
    connect_timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS
    read_timeout_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS
    request_interval_seconds: float = DEFAULT_REQUEST_INTERVAL_SECONDS
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    backoff_initial_seconds: float = DEFAULT_BACKOFF_INITIAL_SECONDS
    backoff_max_seconds: float = DEFAULT_BACKOFF_MAX_SECONDS
    retry_after_max_seconds: float = DEFAULT_RETRY_AFTER_MAX_SECONDS
    raw_dir: Path = DEFAULT_RAW_DIR
    products_path: Path = DEFAULT_PRODUCTS_PATH
    report_path: Path = DEFAULT_REPORT_PATH
    log_path: Path = DEFAULT_LOG_PATH
    resume: bool = True
    category_slug: str | None = None
    subcategory_slugs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.page_size < 1:
            raise ValueError("page_size must be at least 1")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.request_interval_seconds < 0:
            raise ValueError("request_interval_seconds cannot be negative")
        if self.subcategory_slugs and self.category_slug is None:
            raise ValueError("subcategory selection requires a category")
