"""Development entry point for the Shufersal pipeline.

Use this while building and testing. It avoids downloading the full dataset.

Examples:
    uv run python scripts/run_shufersal_dev.py
    uv run python scripts/run_shufersal_dev.py --download --max-files 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_extraction.process_shufersal import main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Shufersal pipeline in dev mode.")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download files from Shufersal instead of using local files only.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=3,
        help="Maximum number of files to download (only used with --download).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.download:
        main(download=True, max_files=args.max_files)
    else:
        main(download=False)
