"""Freeze human-reviewed v2 gold from the annotations workspace.

Only rows with status accepted/corrected are written (excluded dropped).
Requires every non-excluded row to be reviewed unless --allow-partial.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from src.slm_benchmark.annotation_io import (
    V2_ANNOTATIONS_CSV,
    V2_GOLD_CSV,
    V2_GOLD_MANIFEST,
    V2_BENCHMARK_VERSION,
    load_annotations,
    write_gold_csv,
)
from src.slm_benchmark.annotation_schema import AnnotationStatus

logger = logging.getLogger(__name__)

REVIEWED = {AnnotationStatus.ACCEPTED, AnnotationStatus.CORRECTED}
TERMINAL = REVIEWED | {AnnotationStatus.EXCLUDED}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze v2 gold CSV from reviews.")
    parser.add_argument("--annotations", type=Path, default=V2_ANNOTATIONS_CSV)
    parser.add_argument("--output", type=Path, default=V2_GOLD_CSV)
    parser.add_argument("--manifest", type=Path, default=V2_GOLD_MANIFEST)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Allow freeze while some rows remain unreviewed (smoke only).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing frozen gold file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.output.exists() and not args.force:
        logger.error("%s exists. Pass --force to overwrite.", args.output)
        return 1

    rows = load_annotations(args.annotations)
    status_counts = Counter(row.annotation_status.value for row in rows)
    unreviewed = [
        row for row in rows if row.annotation_status == AnnotationStatus.UNREVIEWED
    ]
    if unreviewed and not args.allow_partial:
        logger.error(
            "%s row(s) still unreviewed. Finish review_annotations or pass "
            "--allow-partial.",
            len(unreviewed),
        )
        return 1

    gold_rows = [row for row in rows if row.annotation_status in REVIEWED]
    if not gold_rows:
        logger.error("No accepted/corrected rows to freeze.")
        return 1

    write_gold_csv(gold_rows, args.output)
    manifest = {
        "benchmark_version": V2_BENCHMARK_VERSION,
        "source_annotations": str(args.annotations),
        "n_annotations_total": len(rows),
        "n_gold": len(gold_rows),
        "n_excluded": status_counts.get("excluded", 0),
        "n_unreviewed_skipped": len(unreviewed),
        "status_counts": dict(status_counts),
        "sha256": file_sha256(args.output),
        "leakage_policy": (
            "Frozen v2 gold item_codes (same population as v1) must never be "
            "included in future SFT/LoRA training datasets."
        ),
        "note": (
            "Gold English / SKU fields require human accepted or corrected "
            "status. Candidates are not gold."
        ),
    }
    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "Froze %s gold row(s) to %s (sha256=%s)",
        len(gold_rows),
        args.output,
        manifest["sha256"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
