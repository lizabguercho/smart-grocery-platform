"""CLI human review for v2 annotation candidates.

Keys:
  a  accept candidates → gold, status=accepted
  e  edit English name then accept remaining candidate structs
  c  correct fields interactively, status=corrected
  x  exclude row
  n  add/replace note
  s  skip (leave unreviewed)
  q  quit (progress saved)

Usage:
  PYTHONPATH=. uv run python -m src.slm_benchmark.review_annotations
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.slm_benchmark.annotation_io import (
    V2_ANNOTATIONS_CSV,
    load_annotations,
    write_annotations,
)
from src.slm_benchmark.annotation_schema import AnnotationRow, AnnotationStatus

logger = logging.getLogger(__name__)


def _prompt(message: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{message}{suffix}: ").strip()
    return value if value else default


def _opt_float(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    return float(text)


def _show(row: AnnotationRow, index: int, total: int) -> None:
    print()
    print("=" * 72)
    print(f"[{index}/{total}] item_code={row.item_code}  status={row.annotation_status.value}")
    print(f"Hebrew: {row.raw_item_name}")
    print(f"is_product={row.is_product}  category={row.category}")
    if row.manufacture_name:
        print(f"manufacture_hint: {row.manufacture_name}")
    print("--- candidates ---")
    print(f"  name_en:      {row.candidate_name_en}")
    print(f"  brand:        {row.candidate_brand}")
    print(f"  product_type: {row.candidate_product_type}")
    print(f"  variant:      {row.candidate_variant}")
    print(
        f"  quantity:     {row.candidate_quantity}  unit={row.candidate_unit}  "
        f"pack={row.candidate_pack_count}  percent={row.candidate_percent}"
    )
    if row.gold_name_en or row.annotation_status != AnnotationStatus.UNREVIEWED:
        print("--- current gold ---")
        print(f"  name_en:      {row.gold_name_en}")
        print(f"  brand:        {row.gold_brand}")
        print(f"  product_type: {row.gold_product_type}")
        print(f"  variant:      {row.gold_variant}")
        print(
            f"  quantity:     {row.gold_quantity}  unit={row.gold_unit}  "
            f"pack={row.gold_pack_count}  percent={row.gold_percent}"
        )
    if row.annotation_notes:
        print(f"notes: {row.annotation_notes}")
    print("commands: [a]ccept  [e]dit-name  [c]orrect  [x]exclude  [n]ote  [s]kip  [q]uit")


def _correct_fields(row: AnnotationRow) -> None:
    print("Enter values (blank keeps candidate; '-' clears to null).")

    def pick(label: str, candidate: str | None) -> str | None:
        raw = _prompt(label, candidate or "")
        if raw == "-":
            return None
        return raw or None

    def pick_float(label: str, candidate: float | None) -> float | None:
        default = "" if candidate is None else str(candidate)
        raw = _prompt(label, default)
        if raw == "-":
            return None
        if not raw:
            return candidate
        return float(raw)

    row.gold_name_en = pick("gold_name_en", row.candidate_name_en)
    row.gold_brand = pick("gold_brand", row.candidate_brand)
    row.gold_product_type = pick("gold_product_type", row.candidate_product_type)
    row.gold_variant = pick("gold_variant", row.candidate_variant)
    row.gold_quantity = pick_float("gold_quantity", row.candidate_quantity)
    row.gold_unit = pick("gold_unit", row.candidate_unit)
    row.gold_pack_count = pick_float("gold_pack_count", row.candidate_pack_count)
    row.gold_percent = pick_float("gold_percent", row.candidate_percent)
    if not row.is_product:
        row.clear_gold_for_non_product()
    row.annotation_status = AnnotationStatus.CORRECTED


def review_loop(rows: list[AnnotationRow], path: Path, *, only_unreviewed: bool) -> int:
    pending = [
        row
        for row in rows
        if (not only_unreviewed)
        or row.annotation_status == AnnotationStatus.UNREVIEWED
    ]
    if not pending:
        print("Nothing to review.")
        return 0

    total = len(pending)
    for index, row in enumerate(pending, start=1):
        _show(row, index, total)
        while True:
            cmd = input("> ").strip().casefold()
            if cmd == "a":
                if not row.is_product:
                    row.clear_gold_for_non_product()
                    row.annotation_status = AnnotationStatus.ACCEPTED
                else:
                    row.accept_candidates()
                break
            if cmd == "e":
                name = _prompt("gold_name_en", row.candidate_name_en or "")
                row.accept_candidates()
                row.gold_name_en = name or None
                row.annotation_status = AnnotationStatus.CORRECTED
                if not row.is_product:
                    row.clear_gold_for_non_product()
                break
            if cmd == "c":
                _correct_fields(row)
                break
            if cmd == "x":
                row.annotation_status = AnnotationStatus.EXCLUDED
                note = _prompt("exclusion note", row.annotation_notes)
                row.annotation_notes = note
                break
            if cmd == "n":
                row.annotation_notes = _prompt("note", row.annotation_notes)
                write_annotations(rows, path)
                continue
            if cmd == "s":
                break
            if cmd == "q":
                write_annotations(rows, path)
                print(f"Saved progress to {path}")
                return 0
            print("Unknown command. Use a/e/c/x/n/s/q.")
        write_annotations(rows, path)

    print(f"Review pass complete. Saved {path}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Human-review v2 annotation candidates.")
    parser.add_argument("--annotations", type=Path, default=V2_ANNOTATIONS_CSV)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Re-review even already accepted/corrected/excluded rows.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    if not args.annotations.is_file():
        print(
            f"Missing {args.annotations}. Run annotate_candidates first.",
            file=sys.stderr,
        )
        return 1
    rows = load_annotations(args.annotations)
    return review_loop(rows, args.annotations, only_unreviewed=not args.all)


if __name__ == "__main__":
    sys.exit(main())
