"""Apply reviewed tobacco-category overrides to unlabeled product predictions.

Requirements:
- Leaves data/processed/unlabeled_product_predictions.csv untouched.
- Reads review items from data/processed/unlabeled_tobacco_review.csv.
- Confirms approved tobacco products and holds ambiguous items for manual review.
- Writes approved overrides to data/processed/approved_tobacco_overrides.csv.
- Writes final combined predictions to data/processed/unlabeled_product_classifications.csv.
- Does not modify ML model code or 12-class label mappings.
- Does not write to PostgreSQL.

Run:
  PYTHONPATH=. .venv/bin/python -u scripts/apply_tobacco_overrides.py
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

PREDICTIONS_PATH = Path("data/processed/unlabeled_product_predictions.csv")
REVIEW_PATH = Path("data/processed/unlabeled_tobacco_review.csv")
APPROVED_OVERRIDES_PATH = Path("data/processed/approved_tobacco_overrides.csv")
AMBIGUOUS_REVIEW_PATH = Path("data/processed/ambiguous_tobacco_review.csv")
FINAL_COMBINED_PATH = Path("data/processed/unlabeled_product_classifications.csv")

TARGET_CATEGORY = "Tobacco & Smoking Accessories"
TARGET_METHOD = "manual_rule"

# Known ambiguous items from the review file that lack manufacturer confirmation
# and explicit 'סיגריות' or 'טבק' nouns, held for human confirmation.
AMBIGUOUS_ITEM_CODES = {
    "72983454",      # גולף סופר סלימס בודד (no mfg, Golf brand)
    "72983997",      # גולף גולד 100 קופסא קשיחה (no mfg, Golf brand)
    "72984000",      # גולף סילבר ארוך חפיסה (no mfg, Golf brand)
    "72991398",      # טיים בלו 83 (no mfg, Time brand)
    "72991428",      # ברודווי 100 (no mfg, Broadway brand)
    "72991466",      # גולף גולד 100 (no mfg, Golf brand)
    "7290000302126",  # פאקט אירופה (no mfg, generic Europe carton)
}


def load_review_items(
    review_path: Path,
) -> tuple[dict[str, dict[str, str]], list[dict[str, str]]]:
    """Load review items and partition into approved overrides vs ambiguous items."""
    approved_overrides: dict[str, dict[str, str]] = {}
    ambiguous_items: list[dict[str, str]] = []

    with review_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = str(row["item_code"]).strip()
            if code in AMBIGUOUS_ITEM_CODES:
                ambiguous_items.append(row)
            else:
                approved_overrides[code] = row

    return approved_overrides, ambiguous_items


def build_final_classifications(
    raw_predictions_path: Path,
    approved_overrides: dict[str, dict[str, str]],
) -> list[dict[str, str | bool]]:
    """Build the final combined classification dataset."""
    combined_rows: list[dict[str, str | bool]] = []

    with raw_predictions_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = str(row["item_code"]).strip()
            item_name = row["item_name"]
            mfg_name = row["manufacture_name"]
            pred_cat = row["predicted_category"]

            if code in approved_overrides:
                override = approved_overrides[code]
                combined_rows.append(
                    {
                        "item_code": code,
                        "item_name": item_name,
                        "manufacture_name": mfg_name,
                        "predicted_category": pred_cat,
                        "final_category": TARGET_CATEGORY,
                        "classification_method": TARGET_METHOD,
                        "include_in_analysis": False,
                        "exclusion_reason": override.get("exclusion_reason", "tobacco_manual_override"),
                    }
                )
            else:
                combined_rows.append(
                    {
                        "item_code": code,
                        "item_name": item_name,
                        "manufacture_name": mfg_name,
                        "predicted_category": pred_cat,
                        "final_category": pred_cat,
                        "classification_method": row.get("classification_method", "tfidf_linear_svm"),
                        "include_in_analysis": True,
                        "exclusion_reason": "",
                    }
                )

    return combined_rows


def save_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Save records to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def validate_results(
    raw_predictions_path: Path,
    final_rows: list[dict],
    approved_overrides: dict[str, dict[str, str]],
    ambiguous_items: list[dict[str, str]],
) -> None:
    """Validate all integrity assertions."""
    # 1. Raw file length check
    with raw_predictions_path.open("r", encoding="utf-8") as f:
        raw_count = sum(1 for _ in csv.DictReader(f))
    assert raw_count == 9098, f"Expected 9,098 raw rows, got {raw_count}"

    # 2. Final row count preservation
    assert len(final_rows) == raw_count, f"Expected {raw_count} final rows, got {len(final_rows)}"

    # 3. Item code uniqueness
    final_codes = [r["item_code"] for r in final_rows]
    assert len(final_codes) == len(set(final_codes)), "Duplicate item_code values found in final output"

    # 4. Correct number of overrides
    overridden = [r for r in final_rows if r["final_category"] == TARGET_CATEGORY]
    assert len(overridden) == len(approved_overrides), (
        f"Expected {len(approved_overrides)} overrides, got {len(overridden)}"
    )

    # 5. Only approved items receive override
    overridden_codes = {r["item_code"] for r in overridden}
    assert overridden_codes == set(approved_overrides.keys()), (
        "Mismatch between approved item codes and overridden item codes"
    )

    # 6. Ambiguous items must NOT receive override
    ambiguous_codes = {r["item_code"] for r in ambiguous_items}
    for r in final_rows:
        if r["item_code"] in ambiguous_codes:
            assert r["final_category"] != TARGET_CATEGORY, (
                f"Ambiguous item {r['item_code']} incorrectly received override"
            )
            assert r["include_in_analysis"] is True, (
                f"Ambiguous item {r['item_code']} incorrectly excluded"
            )

    # 7. No empty categories
    for r in final_rows:
        assert r["final_category"], f"Row {r['item_code']} has empty final_category"
        assert r["classification_method"], f"Row {r['item_code']} has empty classification_method"


def main() -> None:
    print(f"Reading review items from {REVIEW_PATH}...", flush=True)
    approved_overrides, ambiguous_items = load_review_items(REVIEW_PATH)
    print(f"  Approved tobacco items: {len(approved_overrides)}", flush=True)
    print(f"  Ambiguous items held for review: {len(ambiguous_items)}", flush=True)

    # 1. Save approved overrides artifact
    approved_rows = []
    for code, row in approved_overrides.items():
        approved_rows.append(
            {
                "item_code": code,
                "item_name": row["item_name"],
                "manufacture_name": row["manufacture_name"],
                "predicted_category": row["predicted_category"],
                "final_category": TARGET_CATEGORY,
                "classification_method": TARGET_METHOD,
                "include_in_analysis": False,
                "exclusion_reason": row["exclusion_reason"],
            }
        )
    override_fields = [
        "item_code",
        "item_name",
        "manufacture_name",
        "predicted_category",
        "final_category",
        "classification_method",
        "include_in_analysis",
        "exclusion_reason",
    ]
    save_csv(APPROVED_OVERRIDES_PATH, override_fields, approved_rows)
    print(f"Saved approved overrides to: {APPROVED_OVERRIDES_PATH}", flush=True)

    # 2. Save ambiguous items artifact for manual review
    ambiguous_fields = [
        "item_code",
        "item_name",
        "manufacture_name",
        "predicted_category",
        "exclusion_reason",
    ]
    save_csv(AMBIGUOUS_REVIEW_PATH, ambiguous_fields, ambiguous_items)
    print(f"Saved ambiguous review items to: {AMBIGUOUS_REVIEW_PATH}", flush=True)

    # 3. Build final combined classification dataset
    print(f"Reading raw predictions from {PREDICTIONS_PATH}...", flush=True)
    final_rows = build_final_classifications(PREDICTIONS_PATH, approved_overrides)
    save_csv(FINAL_COMBINED_PATH, override_fields, final_rows)
    print(f"Saved combined classifications to: {FINAL_COMBINED_PATH}", flush=True)

    # 4. Validate
    validate_results(PREDICTIONS_PATH, final_rows, approved_overrides, ambiguous_items)
    print("All validation assertions passed successfully!", flush=True)

    # 5. Print category distribution
    print("\n=== FINAL CATEGORY DISTRIBUTION ===", flush=True)
    cat_counts = Counter(r["final_category"] for r in final_rows)
    total = len(final_rows)
    for cat, count in cat_counts.most_common():
        pct = (count / total) * 100
        print(f"  {cat:<32} {count:>5} ({pct:>5.2f}%)", flush=True)

    print("\n=== CLASSIFICATION METHOD BREAKDOWN ===", flush=True)
    method_counts = Counter(r["classification_method"] for r in final_rows)
    for method, count in method_counts.most_common():
        pct = (count / total) * 100
        print(f"  {method:<32} {count:>5} ({pct:>5.2f}%)", flush=True)

    print("\n=== ANALYSIS INCLUSION BREAKDOWN ===", flush=True)
    incl_counts = Counter(r["include_in_analysis"] for r in final_rows)
    for incl, count in incl_counts.most_common():
        pct = (count / total) * 100
        status_label = "Included in analysis (True)" if incl else "Excluded from analysis (False)"
        print(f"  {status_label:<32} {count:>5} ({pct:>5.2f}%)", flush=True)


if __name__ == "__main__":
    main()
