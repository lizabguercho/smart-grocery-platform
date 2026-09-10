"""Flag obvious tobacco products in unlabeled_product_predictions.csv for manual review.

Does not modify unlabeled_product_predictions.csv.
Does not write to PostgreSQL.

Run:
  PYTHONPATH=. .venv/bin/python -u scripts/flag_unlabeled_tobacco_products.py
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

INPUT_PATH = Path("data/processed/unlabeled_product_predictions.csv")
OUTPUT_PATH = Path("data/processed/unlabeled_tobacco_review.csv")

# Distinct tobacco brands with near-zero false-positive risk in grocery catalogs
DISTINCT_CIGARETTE_BRANDS = (
    "מרלבורו",     # Marlboro
    "פרלמנט",      # Parliament
    "וינסטון",     # Winston
    "ווינסטון",    # Winston (alt spelling)
    "פאלמאל",      # Pall Mall
    "פאל מאל",     # Pall Mall (spaced)
    "נובלס",       # Noblesse
    "צסטרפילד",    # Chesterfield
    "צ'סטרפילד",   # Chesterfield (with quote)
    "מונטנה פילטר", # Montana filter
)


def get_tobacco_exclusion_reason(name: str) -> str | None:
    """Return an exclusion reason if the product name matches conservative tobacco rules.

    Rules avoid generic substrings (such as 'קנט' matching 'פיקנטי' or 'סיגר'
    matching 'עלי סיגר מרוקאי') to avoid false positives.
    """
    text = name.strip()

    # Rule 1: Distinct global cigarette brand names
    for brand in DISTINCT_CIGARETTE_BRANDS:
        if brand in text:
            return f"tobacco_brand_{brand}"

    # Rule 2: Camel / כאמל / קאמל
    if "כאמל" in text or "קאמל" in text:
        return "tobacco_brand_camel"

    # Rule 3: L&M variations (אל אם / אל אמ / ל.מ)
    if any(lm in text for lm in ("אל אם", "אל אמ", "ל.מ רד", "ל.מ ")):
        return "tobacco_brand_lm"

    # Rule 4: LD (אל די) - excluding laundry brand Ariel Diplomat
    if "אל די" in text and "אריאל" not in text:
        return "tobacco_brand_ld"

    # Rule 5: Next (נקסט)
    if "נקסט" in text:
        return "tobacco_brand_next"

    # Rule 6: Golf (גולף) in cigarette context (slims, gold, silver, cigarettes, 100)
    if "גולף" in text and any(g in text for g in ("סלימס", "גולד", "סילבר", "סיגריות", "100")):
        return "tobacco_brand_golf"

    # Rule 7: Time (טיים) in cigarette context (red, blue, 83, pack, carton)
    if "טיים" in text and any(t in text for t in ("רד", "בלו", "83", "פאקט", "חפיסה")):
        return "tobacco_brand_time"

    # Rule 8: Vogue (ווג) - excluding fruit beverages (פרוט&ווג)
    if "ווג" in text and "פרוט" not in text:
        return "tobacco_brand_vogue"

    # Rule 9: Kent (קנט) as a whole word - excluding spicy foods (פיקנטי)
    if (" קנט " in f" {text} " or text.startswith("קנט ")) and "פיקנט" not in text:
        return "tobacco_brand_kent"

    # Rule 10: Specific domestic cigarette brands
    if "גולדן ירוק" in text:
        return "tobacco_brand_golden"
    if "אירופה" in text and "פאקט" in text:
        return "tobacco_brand_europa"
    if "ברודווי" in text:
        return "tobacco_brand_broadway"

    # Rule 11: Explicit tobacco & cigarette product types
    if "סיגריות" in text:
        return "tobacco_product_cigarettes"
    if "טבק" in text:
        return "tobacco_product_tobacco"

    # Rule 12: Rolling paper and cigarette filter accessories
    if "גלגול" in text and any(kw in text for kw in ("ניר", "נייר", "קונוס", "טבק")):
        return "tobacco_accessory_rolling_paper"
    if "פילטר" in text and "פארטי" in text:
        return "tobacco_accessory_cigarette_filters"

    return None


def main() -> None:
    print(f"Reading predictions from {INPUT_PATH}...", flush=True)
    df = pd.read_csv(INPUT_PATH, dtype={"item_code": str})
    print(f"Total raw predictions loaded: {len(df)}", flush=True)

    flagged_rows = []
    for row in df.itertuples(index=False):
        reason = get_tobacco_exclusion_reason(str(row.item_name))
        if reason is not None:
            flagged_rows.append(
                {
                    "item_code": str(row.item_code),
                    "item_name": row.item_name,
                    "manufacture_name": row.manufacture_name,
                    "predicted_category": row.predicted_category,
                    "exclusion_reason": reason,
                }
            )

    flagged_df = pd.DataFrame(flagged_rows)
    print(f"Flagged tobacco products: {len(flagged_df)}", flush=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    flagged_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    print(f"Saved review file to: {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
