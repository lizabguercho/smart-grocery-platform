"""Names that are not grocery SKUs — used only when choosing translation rows.

Does not delete anything from PostgreSQL. ETL still stores these barcodes.

The first four phrases are the comparability-audit `collision_keyword`
rule (docs/comparability_audit.md). The rest are the same idea for
e-commerce fees and meal-card lines that the audit list did not cover.
"""

from __future__ import annotations

# Substrings. A name is skipped for translation if any of these appear.
TRANSLATION_NAME_EXCLUSIONS: tuple[str, ...] = (
    "דמי משלוח",
    "הנחות",
    "חזרות",
    "הפרשים",
    "דמי מישלוח",
    "משלוח אינטרנט",
    "מישלוח לבית",
    "איסוף עצמי",
    "סיבוס",
    "תן ביס",
    "פטור מעמ",
    "גודי פטור",
)


def is_excluded_from_translation(item_name: str) -> bool:
    """True for delivery fees, pickup SKUs, Cibus/Ten Bis vouchers, and similar."""

    name = item_name or ""
    return any(marker in name for marker in TRANSLATION_NAME_EXCLUSIONS)


def exclusion_like_patterns() -> list[str]:
    """SQL ILIKE patterns: %marker% for each excluded phrase."""

    return [f"%{marker}%" for marker in TRANSLATION_NAME_EXCLUSIONS]
