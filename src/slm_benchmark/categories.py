"""Canonical grocery category labels for the SLM benchmark.

Re-exports the project's fixed 12-class taxonomy so the prompt and
validators never invent a parallel label list.
"""

from __future__ import annotations

from src.product_classification.transformer_classifier import CATEGORIES

ALLOWED_CATEGORIES: tuple[str, ...] = CATEGORIES

__all__ = ["ALLOWED_CATEGORIES", "CATEGORIES"]
