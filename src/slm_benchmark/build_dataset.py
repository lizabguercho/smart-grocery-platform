"""One-shot builder for the frozen SLM grocery-understanding benchmark.

Never called by the experiment runner. Re-running overwrites the frozen
files only when --force is passed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from src.database_loader.connection import get_connection, get_remote_connection
from src.product_classification.comparable_labels import EXCLUDED_ITEM_CODES
from src.product_classification.comparable_labels import (
    DEFAULT_ANALYSIS_CSV_PATH,
)
from src.product_translation.exclusions import is_excluded_from_translation

# Substrings that are too broad alone (e.g. חזרות matches "להחזרות" on yogurt).
# For the non-product gold slice, prefer fee/voucher markers.
STRONG_NON_PRODUCT_MARKERS: tuple[str, ...] = (
    "דמי משלוח",
    "דמי מישלוח",
    "משלוח אינטרנט",
    "מישלוח לבית",
    "איסוף עצמי",
    "סיבוס",
    "תן ביס",
    "פטור מעמ",
    "גודי פטור",
)
from src.product_translation.config import HEBREW_LETTER_RANGE
from src.slm_benchmark import BENCHMARK_VERSION
from src.slm_benchmark.categories import ALLOWED_CATEGORIES
from src.slm_benchmark.dataset import (
    DEFAULT_BENCHMARK_CSV,
    DEFAULT_MANIFEST_PATH,
    write_benchmark_csv,
)
from src.slm_benchmark.metrics import category_histogram, slice_counts
from src.slm_benchmark.schema import BenchmarkRow

logger = logging.getLogger(__name__)

DEFAULT_SEED = 42
DEFAULT_PER_CATEGORY = 18
DEFAULT_NON_PRODUCT_TARGET = 40
LATIN_LETTER = re.compile(r"[A-Za-z]")
DIGIT = re.compile(r"\d")


def contains_hebrew(text: str) -> bool:
    start, end = HEBREW_LETTER_RANGE
    return any(start <= ord(ch) <= end for ch in text)


def slice_tags_for(name: str, *, is_product: bool) -> str:
    tags: list[str] = []
    if not is_product:
        tags.append("non_product")
    hebrew = contains_hebrew(name)
    latin = bool(LATIN_LETTER.search(name))
    if hebrew and latin:
        tags.append("mixed_script")
    elif hebrew:
        tags.append("hebrew_only")
    elif latin:
        tags.append("latin_only")
    if DIGIT.search(name):
        tags.append("has_digits")
    tokens = name.split()
    if len(tokens) <= 2:
        tags.append("short_name")
    if len(tokens) >= 8 or len(name) >= 45:
        tags.append("long_name")
    return "|".join(tags)


def load_eligible_products(
    analysis_csv: Path,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    rows: list[dict[str, str]] = []
    source_counts: Counter[str] = Counter()
    with analysis_csv.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            source_counts[raw["category"]] += 1
            if str(raw.get("include_in_analysis", "")).strip() not in {"True", "true", "1"}:
                continue
            item_code = str(raw["item_code"]).strip()
            if item_code in EXCLUDED_ITEM_CODES:
                continue
            name = (raw.get("item_name") or "").strip()
            if not name:
                continue
            if is_excluded_from_translation(name):
                continue
            category = (raw.get("category") or "").strip()
            if category not in ALLOWED_CATEGORIES:
                continue
            rows.append(
                {
                    "item_code": item_code,
                    "raw_item_name": name,
                    "category": category,
                    "subcategory": (raw.get("subcategory") or "").strip(),
                    "manufacture_name": (raw.get("manufacturer") or "").strip(),
                }
            )
    return rows, dict(sorted(source_counts.items()))


def _is_strong_non_product(item_name: str) -> bool:
    name = item_name or ""
    return any(marker in name for marker in STRONG_NON_PRODUCT_MARKERS)


def _synthetic_non_products(target: int, reserved_codes: set[str]) -> list[dict[str, str]]:
    """Deterministic fee/voucher names when the DB has too few real rows."""

    templates = [
        "דמי משלוח",
        "דמי משלוח אינטרנט",
        "דמי מישלוח אינטרנט",
        "משלוח אינטרנט",
        "מישלוח לבית הלקוח",
        "איסוף עצמי-אינטרנט",
        "איסוף עצמי",
        "תו סיבוס פטור מעמ",
        "תן ביס פטור מעמ",
        "גודי פטור מעמ",
        "דמי משלוח רמי לוי",
        "משלוח אינטרנט שופרסל",
        "איסוף עצמי סניף",
        "סיבוס פטור מעמ",
        "תן ביס שובר",
        "דמי מישלוח",
        "משלוח אינטרנט מהיר",
        "איסוף עצמי ללא תשלום",
        "גודי פטור",
        "פטור מעמ סיבוס",
        "דמי משלוח ללקוח",
        "משלוח אינטרנט אקספרס",
        "מישלוח לבית",
        "איסוף עצמי אינטרנט",
        "תו תן ביס פטור מעמ",
        "דמי משלוח הזמנה",
        "משלוח אינטרנט בסיסי",
        "דמי מישלוח לבית",
        "איסוף עצמי חנות",
        "סיבוס ארוחה פטור מעמ",
        "תן ביס פטור",
        "גודי פטור מעמ הזמנה",
        "דמי משלוח סופר",
        "משלוח אינטרנט סוף שבוע",
        "איסוף עצמי הזמנה",
        "דמי משלוח כללי",
        "מישלוח לבית הלקוח אקספרס",
        "תו סיבוס",
        "תן ביס כרטיס",
        "גודי פטור מס",
    ]
    rows: list[dict[str, str]] = []
    for index, name in enumerate(templates, start=1):
        if not _is_strong_non_product(name):
            continue
        code = f"np-{index:03d}"
        if code in reserved_codes:
            continue
        rows.append(
            {
                "item_code": code,
                "raw_item_name": name,
                "manufacture_name": "",
            }
        )
        if len(rows) >= target:
            break
    return rows


def _fetch_non_product_rows(limit: int, seed: int) -> list[dict[str, str]]:
    """Pull fee/voucher-like names from local DB, then remote if needed."""

    patterns = [f"%{marker}%" for marker in STRONG_NON_PRODUCT_MARKERS]
    sql = """
        SELECT item_code, item_name, manufacture_name
        FROM grocery.products
        WHERE item_name IS NOT NULL
          AND btrim(item_name) <> ''
          AND item_name ILIKE ANY(%s)
        ORDER BY item_code
        LIMIT %s
    """

    def _query(get_conn) -> list[dict[str, str]]:
        with get_conn() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (patterns, limit * 10))
                fetched = cursor.fetchall()
        return [
            {
                "item_code": str(row[0]),
                "raw_item_name": row[1],
                "manufacture_name": (row[2] or "").strip(),
            }
            for row in fetched
            if _is_strong_non_product(row[1] or "")
        ]

    try:
        rows = _query(get_connection)
        if rows:
            logger.info("Loaded %s non-product candidates from local DB", len(rows))
            return rows
    except Exception:
        logger.exception("Local DB non-product fetch failed; trying remote")

    try:
        rows = _query(get_remote_connection)
        logger.info("Loaded %s non-product candidates from remote DB", len(rows))
        return rows
    except Exception:
        logger.exception("Remote DB non-product fetch failed")
        return []

def stratified_sample_products(
    candidates: list[dict[str, str]],
    *,
    per_category: int,
    seed: int,
) -> list[dict[str, str]]:
    rng = random.Random(seed)
    by_category: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_names: set[str] = set()
    for row in candidates:
        name_key = row["raw_item_name"].strip().casefold()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        by_category[row["category"]].append(row)

    sampled: list[dict[str, str]] = []
    for category in ALLOWED_CATEGORIES:
        pool = list(by_category.get(category, []))
        rng.shuffle(pool)
        take = min(per_category, len(pool))
        sampled.extend(pool[:take])
        if take < per_category:
            logger.warning(
                "Category %s has only %s eligible unique names (wanted %s)",
                category,
                take,
                per_category,
            )
    return sampled


def sample_non_products(
    candidates: list[dict[str, str]],
    *,
    target: int,
    seed: int,
    reserved_codes: set[str],
) -> list[dict[str, str]]:
    rng = random.Random(seed + 1)
    pool: list[dict[str, str]] = []
    seen_names: set[str] = set()
    for row in candidates:
        code = row["item_code"]
        if code in reserved_codes:
            continue
        name_key = row["raw_item_name"].strip().casefold()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        pool.append(row)
    rng.shuffle(pool)
    return pool[:target]


def build_rows(
    *,
    analysis_csv: Path,
    seed: int,
    per_category: int,
    non_product_target: int,
) -> tuple[list[BenchmarkRow], dict]:
    products, source_composition = load_eligible_products(analysis_csv)
    product_sample = stratified_sample_products(
        products, per_category=per_category, seed=seed
    )
    reserved = {row["item_code"] for row in product_sample}
    non_product_candidates = _fetch_non_product_rows(non_product_target, seed)
    non_product_sample = sample_non_products(
        non_product_candidates,
        target=non_product_target,
        seed=seed,
        reserved_codes=reserved,
    )
    if len(non_product_sample) < non_product_target:
        needed = non_product_target - len(non_product_sample)
        reserved |= {row["item_code"] for row in non_product_sample}
        synthetic = _synthetic_non_products(needed, reserved)
        # Avoid exact name duplicates against DB-sourced fee rows.
        existing_names = {
            row["raw_item_name"].strip().casefold() for row in non_product_sample
        }
        for row in synthetic:
            if row["raw_item_name"].strip().casefold() in existing_names:
                continue
            non_product_sample.append(row)
            existing_names.add(row["raw_item_name"].strip().casefold())
            if len(non_product_sample) >= non_product_target:
                break
        logger.info(
            "Padded non-product slice to %s with synthetic fee/voucher names",
            len(non_product_sample),
        )

    rows: list[BenchmarkRow] = []
    for row in product_sample:
        rows.append(
            BenchmarkRow(
                benchmark_version=BENCHMARK_VERSION,
                item_code=row["item_code"],
                raw_item_name=row["raw_item_name"],
                is_product=True,
                category=row["category"],
                subcategory=row["subcategory"] or None,
                manufacture_name=row["manufacture_name"] or None,
                slice_tags=slice_tags_for(row["raw_item_name"], is_product=True),
            )
        )
    for row in non_product_sample:
        rows.append(
            BenchmarkRow(
                benchmark_version=BENCHMARK_VERSION,
                item_code=row["item_code"],
                raw_item_name=row["raw_item_name"],
                is_product=False,
                category=None,
                subcategory=None,
                manufacture_name=row.get("manufacture_name") or None,
                slice_tags=slice_tags_for(row["raw_item_name"], is_product=False),
            )
        )

    rows.sort(key=lambda item: (not item.is_product, item.category or "", item.item_code))
    # Seeded shuffle so --limit smoke slices are not a single category block.
    rng = random.Random(seed + 7)
    rng.shuffle(rows)
    manifest = {
        "benchmark_version": BENCHMARK_VERSION,
        "seed": seed,
        "per_category_target": per_category,
        "non_product_target": non_product_target,
        "n_total": len(rows),
        "n_products": sum(1 for row in rows if row.is_product),
        "n_non_products": sum(1 for row in rows if not row.is_product),
        "category_histogram": category_histogram(rows),
        "slice_counts": slice_counts(rows),
        "source_labeled_composition": source_composition,
        "source_analysis_csv": str(analysis_csv),
        "non_product_note": (
            "Non-product rows use strong fee/voucher markers. When the "
            "database has fewer than the target, remaining rows are "
            "synthetic names (item_code prefix np-) built from the same "
            "exclusion phrases. Broad markers like חזרות/הנחות were not "
            "used alone for gold labeling."
        ),
        "leakage_policy": (
            "Frozen benchmark item_codes must never be included in future "
            "SFT/LoRA training datasets. Exact item_name duplicates were "
            "removed within the sample; semantic near-duplicates were not "
            "fully eliminated."
        ),
    }
    return rows, manifest


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the frozen SLM grocery-understanding benchmark."
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--per-category", type=int, default=DEFAULT_PER_CATEGORY)
    parser.add_argument(
        "--non-product-target", type=int, default=DEFAULT_NON_PRODUCT_TARGET
    )
    parser.add_argument(
        "--analysis-csv",
        type=Path,
        default=DEFAULT_ANALYSIS_CSV_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_BENCHMARK_CSV)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing frozen benchmark CSV.",
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
        logger.error(
            "Frozen benchmark already exists at %s. Pass --force to overwrite.",
            args.output,
        )
        return 1
    if not args.analysis_csv.is_file():
        logger.error(
            "Missing %s. Run: PYTHONPATH=. uv run python "
            "scripts/export_labeled_comparable_products.py",
            args.analysis_csv,
        )
        return 1

    rows, manifest = build_rows(
        analysis_csv=args.analysis_csv,
        seed=args.seed,
        per_category=args.per_category,
        non_product_target=args.non_product_target,
    )
    write_benchmark_csv(rows, args.output)
    manifest["sha256"] = file_sha256(args.output)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "Wrote %s rows to %s (products=%s non_products=%s)",
        len(rows),
        args.output,
        manifest["n_products"],
        manifest["n_non_products"],
    )
    logger.info("Manifest: %s sha256=%s", args.manifest, manifest["sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
