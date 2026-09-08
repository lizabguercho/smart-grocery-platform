"""Generate unified classification dataset for Tableau and database loading.

Combines:
1. 5,718 SuperCompare labeled products (with approved manual corrections and exclusions)
2. 9,098 previously unlabeled products (with approved tobacco overrides and baseline ML predictions)

Validates all 14,816 comparable products:
- Exactly 14,816 rows
- Unique item_code
- 14,653 included in analysis
- 163 excluded from analysis

Outputs:
- data/processed/dashboard_product_classification.csv (full artifact with audit fields)
- data/processed/product_classification_table.csv (exact columns for grocery.product_classification)

Run:
  PYTHONPATH=. .venv/bin/python -u scripts/generate_dashboard_classification.py
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from src.product_classification.comparable_labels import (
    EXCLUDED_ITEM_CODES,
    effective_main_category,
    load_category_corrections,
    load_unique_products,
)

COMPARABLE_CSV_PATH = Path("data/processed/comparable_products_with_categories.csv")
SUPERCOMPARE_CSV_PATH = Path("data/processed/supercompare_products.csv")
CORRECTIONS_CSV_PATH = Path("src/product_classification/manual_category_corrections.csv")
UNLABELED_CLASSIFICATIONS_PATH = Path("data/processed/unlabeled_product_classifications.csv")

OUTPUT_DASHBOARD_CSV = Path("data/processed/dashboard_product_classification.csv")
OUTPUT_TABLE_CSV = Path("data/processed/product_classification_table.csv")


def generate_unified_dataset() -> tuple[list[dict], list[dict]]:
    # 1. Load comparable products master list (14,816 items)
    with open(COMPARABLE_CSV_PATH, "r", encoding="utf-8") as f:
        comparable_rows = list(csv.DictReader(f))

    comparable_map = {r["item_code"]: r for r in comparable_rows}
    total_comparable = len(comparable_map)
    print(f"Loaded {total_comparable} comparable products from {COMPARABLE_CSV_PATH}")
    assert total_comparable == 14816, f"Expected 14,816 comparable products, got {total_comparable}"

    # 2. Load SuperCompare products and manual corrections (5,718 labeled products)
    unique_products, dropped = load_unique_products(SUPERCOMPARE_CSV_PATH)
    sc_map = {p.item_code: p for p in unique_products if p.item_code in comparable_map}
    corrections = load_category_corrections(CORRECTIONS_CSV_PATH)
    print(f"Matched {len(sc_map)} labeled products from SuperCompare")
    assert len(sc_map) == 5718, f"Expected 5,718 labeled products, got {len(sc_map)}"

    # 3. Load unlabeled product classifications (9,098 products)
    with open(UNLABELED_CLASSIFICATIONS_PATH, "r", encoding="utf-8") as f:
        unlabeled_rows = list(csv.DictReader(f))

    unlabeled_map = {r["item_code"]: r for r in unlabeled_rows}
    print(f"Loaded {len(unlabeled_map)} classifications from {UNLABELED_CLASSIFICATIONS_PATH}")
    assert len(unlabeled_map) == 9098, f"Expected 9,098 unlabeled classifications, got {len(unlabeled_map)}"

    # 4. Check partition
    labeled_codes = set(sc_map.keys())
    unlabeled_codes = set(unlabeled_map.keys())
    assert len(labeled_codes.intersection(unlabeled_codes)) == 0, "Overlap found between labeled and unlabeled sets!"
    assert (labeled_codes | unlabeled_codes) == set(comparable_map.keys()), "Partition does not cover all comparable products!"

    # 5. Build combined records
    dashboard_rows = []
    table_rows = []

    for code, comp in comparable_map.items():
        item_name = comp.get("item_name", "")
        if code in sc_map:
            p = sc_map[code]
            is_corrected = code in corrections
            final_cat = effective_main_category(code, p.main_category, corrections)
            sub_cat = p.subcategory or ""
            is_included = code not in EXCLUDED_ITEM_CODES
            method = "manual_error_review" if is_corrected else "supercompare_silver"
            reason = "supercompare_label_mismatch_excluded" if not is_included else (
                corrections[code].reason if is_corrected else ""
            )

            dashboard_rows.append({
                "item_code": code,
                "item_name": item_name,
                "category": final_cat,
                "subcategory": sub_cat,
                "include_in_analysis": is_included,
                "classification_method": method,
                "classification_confidence": "",
                "source_group": "labeled_supercompare",
                "predicted_category": "",
                "exclusion_reason": reason,
            })
            table_rows.append({
                "item_code": code,
                "category": final_cat,
                "subcategory": sub_cat,
                "include_in_analysis": is_included,
                "classification_method": method,
                "classification_confidence": "",
            })
        else:
            u = unlabeled_map[code]
            is_included = u["include_in_analysis"] in (True, "True", "true")
            dashboard_rows.append({
                "item_code": code,
                "item_name": item_name,
                "category": u["final_category"],
                "subcategory": "",
                "include_in_analysis": is_included,
                "classification_method": u["classification_method"],
                "classification_confidence": "",
                "source_group": "unlabeled_classified",
                "predicted_category": u["predicted_category"],
                "exclusion_reason": u["exclusion_reason"],
            })
            table_rows.append({
                "item_code": code,
                "category": u["final_category"],
                "subcategory": "",
                "include_in_analysis": is_included,
                "classification_method": u["classification_method"],
                "classification_confidence": "",
            })

    return dashboard_rows, table_rows


def validate_dataset(rows: list[dict]) -> None:
    print("\nRunning validations on generated dataset...")
    total = len(rows)
    assert total == 14816, f"Expected 14,816 total rows, got {total}"

    codes = [r["item_code"] for r in rows]
    assert len(set(codes)) == 14816, "Duplicate item_code values found!"

    included_count = sum(1 for r in rows if r["include_in_analysis"] is True)
    excluded_count = sum(1 for r in rows if r["include_in_analysis"] is False)
    print(f"  Total items: {total}")
    print(f"  Included in analysis (True): {included_count} (expected 14,653)")
    print(f"  Excluded from analysis (False): {excluded_count} (expected 163)")

    assert included_count == 14653, f"Expected 14,653 included items, got {included_count}"
    assert excluded_count == 163, f"Expected 163 excluded items, got {excluded_count}"

    for r in rows:
        assert r["category"], f"Row {r['item_code']} has empty category!"
        assert r["classification_method"], f"Row {r['item_code']} has empty classification_method!"

    print("All Python pre-load validation checks PASSED successfully!\n")


def main() -> None:
    dashboard_rows, table_rows = generate_unified_dataset()
    validate_dataset(dashboard_rows)

    # Save dashboard artifact
    OUTPUT_DASHBOARD_CSV.parent.mkdir(parents=True, exist_ok=True)
    dashboard_fields = [
        "item_code",
        "item_name",
        "category",
        "subcategory",
        "include_in_analysis",
        "classification_method",
        "classification_confidence",
        "source_group",
        "predicted_category",
        "exclusion_reason",
    ]
    with open(OUTPUT_DASHBOARD_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=dashboard_fields)
        writer.writeheader()
        writer.writerows(dashboard_rows)
    print(f"Saved full dashboard classification artifact to: {OUTPUT_DASHBOARD_CSV}")

    # Save table loading artifact
    table_fields = [
        "item_code",
        "category",
        "subcategory",
        "include_in_analysis",
        "classification_method",
        "classification_confidence",
    ]
    with open(OUTPUT_TABLE_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=table_fields)
        writer.writeheader()
        writer.writerows(table_rows)
    print(f"Saved database loading artifact to: {OUTPUT_TABLE_CSV}")

    # Summary
    print("\n=== CLASSIFICATION METHOD BREAKDOWN ===")
    methods = Counter(r["classification_method"] for r in dashboard_rows)
    for m, c in methods.most_common():
        print(f"  {m:<30} {c:>5} ({c/total*100 if (total:=len(dashboard_rows)) else 0:>5.2f}%)")

    print("\n=== FINAL CATEGORY BREAKDOWN ===")
    cats = Counter(r["category"] for r in dashboard_rows)
    for cat, c in cats.most_common():
        print(f"  {cat:<30} {c:>5} ({c/total*100 if (total:=len(dashboard_rows)) else 0:>5.2f}%)")


if __name__ == "__main__":
    main()
