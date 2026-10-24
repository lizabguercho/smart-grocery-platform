"""Conservative normalization for grocery quantity / unit comparison."""

from __future__ import annotations

import re
from typing import Any

# Map common spellings to a small canonical set. No fuzzy brand matching.
UNIT_ALIASES: dict[str, str] = {
    "g": "g",
    "gr": "g",
    "grm": "g",
    "gram": "g",
    "grams": "g",
    "גרם": "g",
    "גר": "g",
    "kg": "kg",
    "kilo": "kg",
    "kilogram": "kg",
    "קג": "kg",
    "קילו": "kg",
    "קילוגרם": "kg",
    "ml": "mL",
    "mls": "mL",
    "milliliter": "mL",
    "millilitre": "mL",
    'מ"ל': "mL",
    "מל": "mL",
    "l": "L",
    "lt": "L",
    "liter": "L",
    "litre": "L",
    "liters": "L",
    "litres": "L",
    "ליטר": "L",
    "ל": "L",
    "units": "units",
    "unit": "units",
    "pcs": "units",
    "pc": "units",
    "יח": "units",
    "יחידות": "units",
    "bags": "bags",
    "bag": "bags",
    "שקיקים": "bags",
    "שקיק": "bags",
}


def normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    text = str(unit).strip()
    if not text:
        return None
    key = text.casefold().replace(".", "").replace(" ", "")
    # Preserve Hebrew keys before casefold mangling for ASCII-only aliases.
    hebrew_key = text.strip()
    if hebrew_key in UNIT_ALIASES:
        return UNIT_ALIASES[hebrew_key]
    if key in UNIT_ALIASES:
        return UNIT_ALIASES[key]
    # Already-canonical short forms.
    if text in {"g", "kg", "mL", "L", "units", "bags"}:
        return text
    if text.casefold() == "ml":
        return "mL"
    return text.casefold()


def normalize_quantity(value: float | int | str | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return None
        value = float(text)
    return float(value)


def quantities_match(
    gold: float | None, pred: float | None, *, rel_tol: float = 1e-6
) -> bool:
    g = normalize_quantity(gold)
    p = normalize_quantity(pred)
    if g is None and p is None:
        return True
    if g is None or p is None:
        return False
    return abs(g - p) <= rel_tol * max(1.0, abs(g))


def units_match(gold: str | None, pred: str | None) -> bool:
    return normalize_unit(gold) == normalize_unit(pred)


def null_aware_str_match(gold: str | None, pred: str | None) -> bool:
    """Exact casefold match; both empty/None counts as a match."""

    g = (gold or "").strip().casefold() or None
    p = (pred or "").strip().casefold() or None
    return g == p


_PACK_RE = re.compile(
    r"(?P<pack>\d+)\s*[x×*]\s*(?P<qty>\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"(?P<pct>\d+(?:[.,]\d+)?)\s*%")
_QTY_UNIT_RE = re.compile(
    r"(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|grm|gr|ml|mL|l|L|גרם|מל|ליטר)?\b",
    re.IGNORECASE,
)


def extract_pack_count_from_text(text: str | None) -> float | None:
    if not text:
        return None
    match = _PACK_RE.search(text)
    if not match:
        return None
    return float(match.group("pack"))


def extract_percent_from_text(text: str | None) -> float | None:
    if not text:
        return None
    match = _PERCENT_RE.search(text)
    if not match:
        return None
    return float(match.group("pct").replace(",", "."))


def extract_quantity_unit_from_text(
    text: str | None,
) -> tuple[float | None, str | None]:
    """Best-effort parse for scoring old preds that only emitted English text.

    Prefer the last quantity+unit pair (usually pack size). Conservative:
    returns (None, None) when ambiguous.
    """

    if not text:
        return None, None
    matches = list(_QTY_UNIT_RE.finditer(text))
    if not matches:
        return None, None
    # Skip bare percentages captured as qty with no unit when % follows.
    for match in reversed(matches):
        start, end = match.span()
        if end < len(text) and text[end : end + 1] == "%":
            continue
        qty = float(match.group("qty").replace(",", "."))
        unit = normalize_unit(match.group("unit"))
        return qty, unit
    return None, None
