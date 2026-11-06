"""Versioned unit registry and deterministic, decimal-safe conversion.

Humans, rules and Qwen all share this module: a system extracts the written
source value and unit, and this code computes the canonical amount.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from src.measurement_extraction.config import UNITS_REGISTRY_VERSION
from src.measurement_extraction.schema import Describes, Measurement, Role, Scope

GRAM = "g"
MILLILITER = "mL"

# Quote-like characters that Hebrew retail text uses inside abbreviations.
_QUOTES = re.compile("[\"'`״׳“”‘’.]")


@dataclass(frozen=True)
class UnitSpec:
    canonical: str
    family: Describes
    factor: Decimal  # multiply the source amount to reach the canonical unit


_G = UnitSpec(GRAM, Describes.MASS, Decimal(1))
_KG = UnitSpec(GRAM, Describes.MASS, Decimal(1000))
_MG = UnitSpec(GRAM, Describes.MASS, Decimal("0.001"))
_ML = UnitSpec(MILLILITER, Describes.VOLUME, Decimal(1))
_L = UnitSpec(MILLILITER, Describes.VOLUME, Decimal(1000))
_CL = UnitSpec(MILLILITER, Describes.VOLUME, Decimal(10))

# Keys are matched after quote stripping and lower-casing. A lone "מ" and bare
# "oz" are deliberately absent: they are ambiguous and stay unresolved.
_ALIASES: dict[str, UnitSpec] = {
    "קג": _KG,
    "קילו": _KG,
    "קילוגרם": _KG,
    "kg": _KG,
    "גרם": _G,
    "גר": _G,
    "ג": _G,
    "g": _G,
    "gr": _G,
    "gram": _G,
    "מג": _MG,
    "מיליגרם": _MG,
    "mg": _MG,
    "ליטר": _L,
    "ל": _L,
    "l": _L,
    "lt": _L,
    "liter": _L,
    "מל": _ML,
    "מיליליטר": _ML,
    "ml": _ML,
    "סל": _CL,
    "cl": _CL,
}
# Aliases are tried longest first when scanning free text.
ALIASES_LONGEST_FIRST = sorted(_ALIASES, key=len, reverse=True)


def normalize_unit_text(text: str) -> str:
    return _QUOTES.sub("", text).strip().lower()


def lookup_unit(source_unit: str | None) -> UnitSpec | None:
    """Return the registered unit for a written unit, or None if unresolved."""

    if not source_unit:
        return None
    return _ALIASES.get(normalize_unit_text(source_unit))


def canonicalize(
    source_amount: Decimal | None, source_unit: str | None
) -> tuple[Decimal | None, str | None, Describes | None]:
    """Compute (amount, unit, family); unknown parts stay None."""

    spec = lookup_unit(source_unit)
    if spec is None:
        return None, None, None
    if source_amount is None:
        return None, spec.canonical, spec.family
    return source_amount * spec.factor, spec.canonical, spec.family


def apply_canonical(entry: Measurement) -> Measurement:
    """Fill amount/unit/describes from the source fields when the unit is known."""

    amount, unit, family = canonicalize(entry.source_amount, entry.source_unit)
    if unit is None:
        return entry
    return entry.model_copy(
        update={
            "amount": amount,
            "unit": unit,
            "describes": entry.describes or family,
        }
    )


def derived_total(entry: Measurement) -> Decimal | None:
    """Read-only preview of total contents; never a stored gold field."""

    if entry.amount is None or entry.measurement_role is not Role.CONTENTS:
        return None
    if entry.amount_scope is Scope.WHOLE_PACKAGE:
        return entry.amount
    if entry.amount_scope is Scope.PER_ITEM and entry.package_count:
        return entry.amount * entry.package_count
    return None


def registry_json() -> dict:
    """Alias table for UI previews, so the page never duplicates conversion rules."""

    return {
        "version": UNITS_REGISTRY_VERSION,
        "quote_chars": _QUOTES.pattern,
        "aliases": {
            alias: {
                "unit": spec.canonical,
                "family": spec.family.value,
                "factor": str(spec.factor),
            }
            for alias, spec in _ALIASES.items()
        },
    }
