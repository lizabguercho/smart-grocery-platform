"""Load the frozen SLM grocery-understanding benchmark."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.slm_benchmark import BENCHMARK_VERSION
from src.slm_benchmark.schema import BenchmarkRow

DEFAULT_BENCHMARK_DIR = Path("data/benchmarks")
DEFAULT_BENCHMARK_CSV = DEFAULT_BENCHMARK_DIR / f"{BENCHMARK_VERSION}.csv"
DEFAULT_MANIFEST_PATH = DEFAULT_BENCHMARK_DIR / f"{BENCHMARK_VERSION}.manifest.json"

BENCHMARK_CSV_FIELDS = (
    "benchmark_version",
    "item_code",
    "raw_item_name",
    "is_product",
    "category",
    "subcategory",
    "manufacture_name",
    "slice_tags",
)


def benchmark_csv_path(benchmark_id: str | Path) -> Path:
    if isinstance(benchmark_id, Path):
        return benchmark_id
    if benchmark_id.endswith(".csv"):
        return Path(benchmark_id)
    return DEFAULT_BENCHMARK_DIR / f"{benchmark_id}.csv"


def load_benchmark(path: str | Path) -> list[BenchmarkRow]:
    csv_path = benchmark_csv_path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Frozen benchmark not found: {csv_path}. "
            "Build it with: uv run python -m src.slm_benchmark.build_dataset"
        )

    rows: list[BenchmarkRow] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row = BenchmarkRow(
                benchmark_version=raw["benchmark_version"],
                item_code=str(raw["item_code"]).strip(),
                raw_item_name=raw["raw_item_name"],
                is_product=str(raw["is_product"]).strip().lower() in {"1", "true", "yes"},
                category=(raw.get("category") or "").strip() or None,
                subcategory=(raw.get("subcategory") or "").strip() or None,
                manufacture_name=(raw.get("manufacture_name") or "").strip() or None,
                slice_tags=(raw.get("slice_tags") or "").strip(),
            )
            if row.benchmark_version != BENCHMARK_VERSION:
                raise ValueError(
                    f"Unexpected benchmark_version {row.benchmark_version!r}; "
                    f"expected {BENCHMARK_VERSION!r}"
                )
            rows.append(row)

    item_codes = [row.item_code for row in rows]
    if len(item_codes) != len(set(item_codes)):
        raise ValueError("Benchmark contains duplicate item_code values")
    return rows


def load_manifest(path: Path | None = None) -> dict:
    manifest_path = path or DEFAULT_MANIFEST_PATH
    with manifest_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_benchmark_csv(rows: list[BenchmarkRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BENCHMARK_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "benchmark_version": row.benchmark_version,
                    "item_code": row.item_code,
                    "raw_item_name": row.raw_item_name,
                    "is_product": row.is_product,
                    "category": row.category or "",
                    "subcategory": row.subcategory or "",
                    "manufacture_name": row.manufacture_name or "",
                    "slice_tags": row.slice_tags,
                }
            )
