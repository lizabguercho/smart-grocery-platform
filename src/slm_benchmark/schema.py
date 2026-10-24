"""Structured prediction schema for grocery-name understanding."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.slm_benchmark.categories import ALLOWED_CATEGORIES

_ALLOWED = frozenset(ALLOWED_CATEGORIES)


class GroceryUnderstandingPrediction(BaseModel):
    """Model output for one product name.

    Tier-1 evaluated fields: ``is_product``, ``category``.
    Tier-2 qualitative fields: brand, normalized_name_en, quantity, unit.
    """

    is_product: bool
    category: str | None = None
    brand: str | None = None
    normalized_name_en: str | None = None
    quantity: float | None = None
    unit: str | None = None

    @field_validator("category", mode="before")
    @classmethod
    def empty_category_to_none(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("brand", "normalized_name_en", "unit", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("category")
    @classmethod
    def category_must_be_allowed(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in _ALLOWED:
            raise ValueError(
                f"category must be one of {sorted(_ALLOWED)}, got {value!r}"
            )
        return value

    def with_non_product_category_cleared(self) -> GroceryUnderstandingPrediction:
        """Return a copy where non-products have category=null (prompt rule)."""

        if self.is_product or self.category is None:
            return self
        return self.model_copy(update={"category": None})


class BenchmarkRow(BaseModel):
    """One frozen benchmark example with Tier-1 gold labels."""

    benchmark_version: str
    item_code: str
    raw_item_name: str
    is_product: bool
    category: str | None = None
    subcategory: str | None = None
    manufacture_name: str | None = None
    slice_tags: str = Field(
        default="",
        description="Pipe-separated deterministic difficulty/slice tags.",
    )

    @property
    def tags(self) -> list[str]:
        if not self.slice_tags.strip():
            return []
        return [tag for tag in self.slice_tags.split("|") if tag]
