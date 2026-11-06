"""System A: deterministic rules over the product title only.

Each rule records an id and the exact character span it matched. Fields the
title does not state stay None; nothing is completed from expectations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from src.measurement_extraction.schema import (
    Annotation,
    Describes,
    Measurement,
    Role,
    Scope,
)
from src.measurement_extraction.units import (
    ALIASES_LONGEST_FIRST,
    apply_canonical,
    lookup_unit,
)

QUOTE = "[\"'`״׳“”.]?"
NUMBER = r"\d+(?:[.,]\d+)?"
# A unit must not run into a longer word: no letter/digit may follow it.
_UNIT_PATTERN = "|".join(
    QUOTE.join(re.escape(c) for c in alias) for alias in ALIASES_LONGEST_FIRST
)
QUANTITY = re.compile(
    rf"(?<![\d.,])({NUMBER})\s*({_UNIT_PATTERN})(?![\w֐-׿])", re.IGNORECASE
)
PERCENT = re.compile(rf"{NUMBER}\s*%")
DIMENSION = re.compile(r"\d+\s*[*xX×]\s*\d+")
COUNT_UNITS = re.compile(r"(?<![\d.,])(\d+)\s*(יח(?:[\"'`״׳.]|ידות)?|יחידות)(?![֐-׿])")
COUNT_NOUNS = re.compile(
    r"(?<![\d.,])(\d+)\s*(שקיות|שקיקים|מברשות|בקבוקים|קפסולות|כוסות|מגבונים|חבילות|קופסאות)(?![\u0590-\u05ff])"
)
COUNT_WORDS = {
    "שלישיית": 3,
    "שלישייה": 3,
    "רביעיית": 4,
    "רביעייה": 4,
    "חמישיית": 5,
    "חמישייה": 5,
}
TRAILING_NUMBER = re.compile(rf"(?<![\d.,])({NUMBER})\s*([\u05d0-\u05ea])?\s*$")
CAPACITY = re.compile(
    r"(?<![\u0590-\u05ff])(?:דלי|מיכל|קנקן|תרמוס|סיר|פח|כד)(?![\u0590-\u05ff])"
)
ANY_DIGITS = re.compile(r"\d+")


@dataclass
class RuleResult:
    annotation: Annotation
    rule_ids: list[str] = field(default_factory=list)
    spans: list[tuple[int, int]] = field(default_factory=list)
    eligible: bool = False  # safe for the cascade to accept without Qwen


def _decimal(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def extract(title: str) -> RuleResult:
    rule_ids: list[str] = []
    spans: list[tuple[int, int]] = []
    consumed: list[tuple[int, int]] = [
        (m.start(), m.end()) for m in PERCENT.finditer(title)
    ]
    consumed += [(m.start(), m.end()) for m in DIMENSION.finditer(title)]

    def free(start: int, end: int) -> bool:
        return not any(start < b and a < end for a, b in consumed)

    entries: list[Measurement] = []
    for match in QUANTITY.finditer(title):
        if not free(match.start(), match.end()) or lookup_unit(match.group(2)) is None:
            continue
        consumed.append((match.start(), match.end()))
        spans.append((match.start(), match.end()))
        rule_ids.append("R_NUM_UNIT")
        entries.append(
            Measurement(
                source_text=match.group(0),
                source_amount=_decimal(match.group(1)),
                source_unit=match.group(2),
            )
        )

    count: int | None = None
    count_match = COUNT_UNITS.search(title) or COUNT_NOUNS.search(title)
    if count_match and free(count_match.start(), count_match.end()):
        count = int(count_match.group(1))
        consumed.append((count_match.start(), count_match.end()))
        spans.append((count_match.start(), count_match.end()))
        rule_ids.append(
            "R_COUNT_UNITS" if COUNT_UNITS.search(title) else "R_COUNT_NOUN"
        )
    else:
        for word, value in COUNT_WORDS.items():
            at = title.find(word)
            if at >= 0:
                count = value
                consumed.append((at, at + len(word)))
                spans.append((at, at + len(word)))
                rule_ids.append("R_COUNT_WORD")
                break

    capacity = CAPACITY.search(title) is not None
    finished = []
    for entry in entries:
        entry = apply_canonical(entry)
        updates: dict = {
            "measurement_role": Role.CAPACITY if capacity else Role.CONTENTS
        }
        if count is not None:
            updates["package_count"] = count  # scope stays unknown: not stated
        elif not capacity:
            updates["amount_scope"] = Scope.WHOLE_PACKAGE
        finished.append(entry.model_copy(update=updates))
    entries = finished

    if not entries and count is not None:
        entries.append(
            Measurement(
                source_text=title[spans[-1][0] : spans[-1][1]],
                describes=Describes.COUNT,
                package_count=count,
            )
        )
    elif not entries:
        tail = TRAILING_NUMBER.search(title)
        if tail and free(tail.start(), tail.end()):
            digits = tail.group(1)
            is_year = len(digits) == 4 and digits[:2] in ("19", "20")
            if not digits.startswith("0") and not is_year:
                spans.append((tail.start(), tail.end()))
                rule_ids.append("R_TRAILING_NUMBER")
                entries.append(
                    Measurement(
                        source_text=tail.group(0).strip(),
                        source_amount=_decimal(digits),
                        source_unit=tail.group(2),
                    )
                )

    leftover = [m for m in ANY_DIGITS.finditer(title) if free(m.start(), m.end())]
    eligible = (
        len(entries) == 1
        and rule_ids == ["R_NUM_UNIT"]
        and entries[0].unit is not None
        and entries[0].amount is not None
        and not leftover
        and not capacity
    )
    return RuleResult(
        Annotation(has_measurement=bool(entries), measurements=entries),
        rule_ids,
        spans,
        eligible,
    )
