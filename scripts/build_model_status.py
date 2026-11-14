"""Regenerate docs/MODEL_STATUS.md from the model changelogs.

PYTHONPATH=. uv run python scripts/build_model_status.py          # write
PYTHONPATH=. uv run python scripts/build_model_status.py --check  # fail if stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.model_lifecycle.changelog import collect, render_status

ROOT = Path(".")
MODELS_DIR = ROOT / "docs" / "models"
STATUS_PATH = ROOT / "docs" / "MODEL_STATUS.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render_status(collect(MODELS_DIR, ROOT))
    if args.check:
        current = (
            STATUS_PATH.read_text(encoding="utf-8") if STATUS_PATH.exists() else ""
        )
        if current != rendered:
            print(
                "docs/MODEL_STATUS.md is stale: run scripts/build_model_status.py",
                file=sys.stderr,
            )
            return 1
        return 0
    STATUS_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {STATUS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
