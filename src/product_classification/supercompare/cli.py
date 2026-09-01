from __future__ import annotations

import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.product_classification.supercompare.client import SuperCompareClient
from src.product_classification.supercompare.config import (
    DEFAULT_CITY,
    DEFAULT_LOG_PATH,
    DEFAULT_PRODUCTS_PATH,
    DEFAULT_RAW_DIR,
    DEFAULT_REPORT_PATH,
    LOG_BACKUP_COUNT,
    LOG_MAX_BYTES,
    SuperCompareConfig,
)
from src.product_classification.supercompare.crawler import SuperCompareCrawler
from src.product_classification.supercompare.storage import SuperCompareBatchStore

CLI_DESCRIPTION = "Crawl and checkpoint SuperCompare product labels."
CATEGORY_HELP = "Limit the crawl to one main-category slug."
SUBCATEGORY_HELP = (
    "Limit the crawl to a subcategory slug; repeat for multiple values. "
    "Requires --category."
)
RESUME_HELP = "Reuse valid page checkpoints (default)."
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=CLI_DESCRIPTION)
    parser.add_argument("--city", default=DEFAULT_CITY)
    parser.add_argument("--category", help=CATEGORY_HELP)
    parser.add_argument(
        "--subcategory",
        action="append",
        default=[],
        help=SUBCATEGORY_HELP,
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=RESUME_HELP,
    )
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_PRODUCTS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS,
        default="INFO",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def config_from_args(args: argparse.Namespace) -> SuperCompareConfig:
    return SuperCompareConfig(
        city=args.city,
        raw_dir=args.raw_dir,
        products_path=args.output,
        report_path=args.report,
        log_path=args.log_file,
        resume=args.resume,
        category_slug=args.category,
        subcategory_slugs=tuple(args.subcategory),
    )


def configure_logging(log_level: str, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        config = config_from_args(args)
    except ValueError as error:
        build_parser().error(str(error))

    configure_logging(args.log_level, config.log_path)
    LOGGER.info("SuperCompare crawl started")

    try:
        with SuperCompareClient(config) as client:
            store = SuperCompareBatchStore(config)
            crawler = SuperCompareCrawler(config, client, store)
            summary = crawler.run()
    except Exception:
        LOGGER.exception("SuperCompare crawl aborted")
        return 1

    if not summary.succeeded:
        LOGGER.error(
            "Crawl completed with %d failures; rerun with --resume",
            len(summary.failures),
        )
        return 1

    LOGGER.info(
        "Crawl completed successfully: %d products saved to %s",
        summary.products,
        summary.products_path,
    )
    return 0
