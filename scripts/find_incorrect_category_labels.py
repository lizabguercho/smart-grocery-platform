"""Find labeled comparable products whose SuperCompare class does not match the name."""

from __future__ import annotations

import csv
from pathlib import Path

from src.product_classification.comparable_labels import DEFAULT_ANALYSIS_CSV_PATH

DEFAULT_MISMATCH_CSV_PATH = Path("data/processed/incorrect_category_labels.csv")

TOBACCO_MARKERS = (
    "פאלמאל",
    "פרלמנט",
    "וינסטון",
    "מרלבורו",
    "סיגריות",
    "קנט קצר",
    "טיים רד",
)
PET_MARKERS = (
    "פנסיפיסט",
    "פנסי פיסט",
    "פנסי פיטס",
    "בונזו לכלב",
    "וויסקס",
)
LITTER_MARKERS = ("חול קריסטל", "חול לחתול", "לחתולים")
TOILET_MARKERS = ("סבון אסלה", "סנובון", "ניקוי אסלות")
OUTPUT_FIELDS = (
    "item_code",
    "item_name",
    "supercompare_product_name",
    "category",
    "subcategory",
    "mismatch_reason",
    "suggested_action",
    "source_url",
)


def _blob(row: dict[str, str]) -> str:
    return f"{row.get('item_name', '')} {row.get('supercompare_product_name', '')}"


def mismatch_reasons(row: dict[str, str]) -> list[str]:
    text = _blob(row)
    category = row.get("category", "")
    subcategory = row.get("subcategory", "")
    reasons: list[str] = []

    if any(marker in text for marker in TOBACCO_MARKERS):
        reasons.append("tobacco_not_a_grocery_class")
    if (
        any(marker in text for marker in PET_MARKERS)
        and subcategory != "Pet Food & Supplies"
    ):
        reasons.append("pet_food_wrong_class")
    if (
        any(marker in text for marker in LITTER_MARKERS)
        and subcategory != "Pet Food & Supplies"
    ):
        reasons.append("pet_litter_wrong_class")
    if (
        any(marker in text for marker in TOILET_MARKERS)
        and category == "Personal Care & Hygiene"
    ):
        reasons.append("toilet_cleaner_in_personal_care")
    if (
        subcategory == "Eggs"
        and "ביצ" not in text
        and ("קפה" in text or "קפאין" in text)
    ):
        reasons.append("coffee_labeled_as_eggs")
    if "מדיח" in text and subcategory == "Laundry":
        reasons.append("dishwasher_labeled_laundry")
    if category == "Baby" and "לוכד צבע" in text:
        reasons.append("laundry_sheet_in_baby")
    if subcategory == "Water" and any(marker in text for marker in LITTER_MARKERS):
        reasons.append("litter_labeled_as_water")
    return reasons


def suggested_action(reasons: list[str]) -> str:
    if "tobacco_not_a_grocery_class" in reasons:
        return "exclude_from_food_analysis"
    if any("pet" in reason or "litter" in reason for reason in reasons):
        return "move_to_pet_or_exclude"
    if "toilet_cleaner_in_personal_care" in reasons:
        return "move_to_household_cleaning"
    if "coffee_labeled_as_eggs" in reasons:
        return "move_to_hot_drinks"
    if "dishwasher_labeled_laundry" in reasons:
        return "move_to_cleaning_products"
    if "laundry_sheet_in_baby" in reasons:
        return "move_to_laundry"
    return "exclude_or_relabel"


def find_mismatches(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for row in rows:
        if not row.get("category"):
            continue
        reasons = mismatch_reasons(row)
        if not reasons:
            continue
        found.append(
            {
                "item_code": row["item_code"],
                "item_name": row["item_name"],
                "supercompare_product_name": row.get("supercompare_product_name", ""),
                "category": row["category"],
                "subcategory": row["subcategory"],
                "mismatch_reason": ";".join(reasons),
                "suggested_action": suggested_action(reasons),
                "source_url": row.get("source_url", ""),
            }
        )
    return found


def write_mismatch_csv(rows: list[dict[str, str]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    mismatches = find_mismatches(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(mismatches)
    return len(mismatches)


def main() -> None:
    with DEFAULT_ANALYSIS_CSV_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    count = write_mismatch_csv(rows, DEFAULT_MISMATCH_CSV_PATH)
    print(f"Wrote {count} suspected incorrect labels to {DEFAULT_MISMATCH_CSV_PATH}")


if __name__ == "__main__":
    main()
