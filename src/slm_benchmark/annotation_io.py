"""CSV IO for v2 annotation / gold files."""

from __future__ import annotations

import csv
from pathlib import Path

from src.slm_benchmark.annotation_schema import (
    ANNOTATION_CSV_FIELDS,
    GOLD_CSV_FIELDS,
    AnnotationRow,
    AnnotationStatus,
    annotation_row_from_dict,
    annotation_row_to_dict,
)
from src.slm_benchmark.dataset import DEFAULT_BENCHMARK_DIR, load_benchmark
from src.slm_benchmark.schema import BenchmarkRow

V2_ANNOTATIONS_CSV = DEFAULT_BENCHMARK_DIR / "slm_grocery_understanding_v2_annotations.csv"
V2_GOLD_CSV = DEFAULT_BENCHMARK_DIR / "slm_grocery_understanding_v2_gold.csv"
V2_GOLD_MANIFEST = DEFAULT_BENCHMARK_DIR / "slm_grocery_understanding_v2_gold.manifest.json"
V2_BENCHMARK_VERSION = "slm_grocery_understanding_v2_gold"


def rows_from_v1(benchmark: list[BenchmarkRow]) -> list[AnnotationRow]:
    return [
        AnnotationRow(
            item_code=row.item_code,
            raw_item_name=row.raw_item_name,
            is_product=row.is_product,
            category=row.category,
            subcategory=row.subcategory,
            manufacture_name=row.manufacture_name,
            slice_tags=row.slice_tags,
            annotation_status=AnnotationStatus.UNREVIEWED,
        )
        for row in benchmark
    ]


def load_annotations(path: Path = V2_ANNOTATIONS_CSV) -> list[AnnotationRow]:
    if not path.is_file():
        raise FileNotFoundError(f"Annotations file not found: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return [annotation_row_from_dict(raw) for raw in csv.DictReader(handle)]


def write_annotations(
    rows: list[AnnotationRow], path: Path = V2_ANNOTATIONS_CSV
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ANNOTATION_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(annotation_row_to_dict(row))


def write_gold_csv(rows: list[AnnotationRow], path: Path = V2_GOLD_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=GOLD_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "benchmark_version": V2_BENCHMARK_VERSION,
                    "item_code": row.item_code,
                    "raw_item_name": row.raw_item_name,
                    "is_product": row.is_product,
                    "category": row.category or "",
                    "subcategory": row.subcategory or "",
                    "manufacture_name": row.manufacture_name or "",
                    "slice_tags": row.slice_tags,
                    "gold_name_en": row.gold_name_en or "",
                    "gold_brand": row.gold_brand or "",
                    "gold_product_type": row.gold_product_type or "",
                    "gold_variant": row.gold_variant or "",
                    "gold_quantity": (
                        "" if row.gold_quantity is None else row.gold_quantity
                    ),
                    "gold_unit": row.gold_unit or "",
                    "gold_pack_count": (
                        "" if row.gold_pack_count is None else row.gold_pack_count
                    ),
                    "gold_percent": (
                        "" if row.gold_percent is None else row.gold_percent
                    ),
                    "annotation_status": row.annotation_status.value,
                    "annotation_notes": row.annotation_notes,
                }
            )


def load_gold(path: Path = V2_GOLD_CSV) -> list[AnnotationRow]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Frozen v2 gold not found: {path}. "
            "Run review + freeze_gold_v2 after annotate_candidates."
        )
    rows: list[AnnotationRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                annotation_row_from_dict(
                    {
                        **raw,
                        # Gold file has no candidate_* columns.
                        "candidate_name_en": "",
                        "candidate_brand": "",
                        "candidate_product_type": "",
                        "candidate_variant": "",
                        "candidate_quantity": "",
                        "candidate_unit": "",
                        "candidate_pack_count": "",
                        "candidate_percent": "",
                        "annotator_model_id": "",
                        "annotated_at": "",
                    }
                )
            )
    return rows
