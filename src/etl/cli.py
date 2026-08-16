from __future__ import annotations

import argparse

from src.etl.constants import DEFAULT_MAX_FILES, DEFAULT_MAX_PAGES
from src.etl.enums import Chain, ExtractType
from src.etl.factory import PipelineFactory
from src.etl.options import PipelineOptions

CLI_DESCRIPTION = "Run the Smart Grocery Platform ETL pipeline."
CHAIN_HELP = "Supermarket chain to extract from."
EXTRACT_HELP = "Dataset to extract."
MAX_FILES_HELP = "Maximum number of files to download (development use)."
MAX_PAGES_HELP = "Maximum Shufersal listing pages to scan (ignored by other chains)."
FULL_HELP = "Download without max-files or max-pages limits."
DOWNLOAD_HELP = "Download source files (default). Use --no-download for local files."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=CLI_DESCRIPTION)
    parser.add_argument(
        "--chain",
        required=True,
        choices=[chain.value for chain in Chain],
        help=CHAIN_HELP,
    )
    parser.add_argument(
        "--extract",
        default=ExtractType.PRICES_FULL.value,
        choices=[extract_type.value for extract_type in ExtractType],
        help=EXTRACT_HELP,
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help=MAX_FILES_HELP,
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=MAX_PAGES_HELP,
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help=FULL_HELP,
    )
    parser.add_argument(
        "--download",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=DOWNLOAD_HELP,
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def options_from_args(args: argparse.Namespace) -> PipelineOptions:
    max_files = None if args.full else args.max_files
    max_pages = None if args.full else args.max_pages
    return PipelineOptions(
        download=args.download,
        max_files=max_files,
        max_pages=max_pages,
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    options = options_from_args(args)
    pipeline = PipelineFactory.create(
        chain=Chain(args.chain),
        extract_type=ExtractType(args.extract),
        options=options,
    )
    pipeline.run()
