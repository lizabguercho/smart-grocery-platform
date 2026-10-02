"""Cheap automatic flags for a bad supermarket-name translation.

These checks cannot prove a name is correct. They only catch the failures
this prompt cares about: leftover Hebrew, dropped numbers, or extra
guessed words.
"""

from __future__ import annotations

import re

from src.product_translation.name_translator import contains_hebrew

NUMBER_TOKEN = re.compile(r"\d+(?:[.,]\d+)?%?")
LATIN_WORD = re.compile(r"[A-Za-z]{3,}")

# English filler the model likes to invent. Not in a typical shelf label
# unless the Hebrew already contains the same idea.
INVENTED_WORDS = frozenset(
    {
        "israel",
        "israeli",
        "imported",
        "delicious",
        "product",
        "fresh",
        "organic",
        "premium",
        "original",
        "authentic",
    }
)

# Only flag these English words when the Hebrew does not already say them.
INVENTED_WORD_HEBREW = {
    "israel": "ישראל",
    "israeli": "ישראל",
    "fresh": "טרי",
    "organic": "אורגני",
    "imported": "יבוא",
}

# Dairy English on a non-dairy Hebrew name is a guessed product.
DAIRY_ENGLISH = frozenset(
    {"milk", "cheese", "yogurt", "yoghurt", "cheddar", "gouda", "cream", "butter"}
)
DAIRY_HEBREW = ("חלב", "גבינה", "יוגורט", "שמנת", "חמאה")

# Words this small model has already hallucinated on grocery names.
HALLUCINATED_ENGLISH = frozenset(
    {
        "jerky",
        "muffin",
        "helper",
        "connection",
        "internet",
        "delivery",
        "online",
        "flavor",
        "fruity",
        "lebanon",
        "israelitas",
        "ozeki",
        "honeycomb",
        "saltpeter",
        "sandwich",
        "cara",
    }
)


def number_tokens(text: str) -> list[str]:
    """Digits and percentages in the order they appear, e.g. 3% 500 1.5."""

    return NUMBER_TOKEN.findall(text or "")


def failure_reasons(hebrew_name: str, english_name: str) -> list[str]:
    """Why this pair looks like a failed literal translation."""

    reasons: list[str] = []
    hebrew = (hebrew_name or "").strip()
    english = (english_name or "").strip()

    if not english:
        reasons.append("empty_english")
        return reasons

    if contains_hebrew(english):
        reasons.append("hebrew_left_in_english")

    missing_numbers = [
        token for token in number_tokens(hebrew) if token not in english
    ]
    if missing_numbers:
        reasons.append("missing_numbers:" + ",".join(missing_numbers))

    extra_numbers = [
        token for token in number_tokens(english) if token not in hebrew
    ]
    if extra_numbers:
        reasons.append("invented_numbers:" + ",".join(extra_numbers))

    invented = sorted(
        {
            word.lower()
            for word in LATIN_WORD.findall(english)
            if word.lower() in INVENTED_WORDS
            and word.lower() not in hebrew.lower()
            and INVENTED_WORD_HEBREW.get(word.lower(), "\0") not in hebrew
        }
    )
    if invented:
        reasons.append("invented_words:" + ",".join(invented))

    english_lower = {word.lower() for word in LATIN_WORD.findall(english)}
    if english_lower & DAIRY_ENGLISH and not any(token in hebrew for token in DAIRY_HEBREW):
        reasons.append("invented_product")

    hallucinated = sorted(english_lower & HALLUCINATED_ENGLISH)
    if hallucinated:
        reasons.append("hallucinated_words:" + ",".join(hallucinated))

    hebrew_parts = hebrew.split()
    english_parts = english.split()
    if hebrew_parts and len(english_parts) > max(8, 2 * len(hebrew_parts)):
        reasons.append("too_many_extra_words")

    return reasons


def is_failed_translation(hebrew_name: str, english_name: str) -> bool:
    return bool(failure_reasons(hebrew_name, english_name))
