"""Semantic schema shared by human gold annotations and model predictions.

Workflow state (draft/saved/needs_review) is bookkeeping and lives outside
the semantic payload, as do split, hashes and run metadata.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Describes(str, Enum):
    MASS = "mass"
    VOLUME = "volume"
    COUNT = "count"
    OTHER = "other"


class Role(str, Enum):
    CONTENTS = "contents"
    CAPACITY = "capacity"


class Scope(str, Enum):
    PER_ITEM = "per_item"
    WHOLE_PACKAGE = "whole_package"


class WorkflowState(str, Enum):
    UNREVIEWED = "unreviewed"
    DRAFT = "draft"
    SAVED = "saved"
    NEEDS_REVIEW = "needs_review"


class Measurement(BaseModel):
    """One measurement entry. Every unresolved field may be None."""

    model_config = ConfigDict(extra="forbid")

    source_text: str | None = None
    source_amount: Decimal | None = None
    source_unit: str | None = None
    amount: Decimal | None = None
    unit: str | None = None
    describes: Describes | None = None
    other_description: str | None = None
    measurement_role: Role | None = None
    amount_scope: Scope | None = None
    package_count: int | None = Field(default=None, ge=1)
    counted_item: str | None = None

    @model_validator(mode="after")
    def _other_needs_description(self) -> Measurement:
        if self.describes is Describes.OTHER and not self.other_description:
            raise ValueError("describes=other requires other_description")
        return self


class Annotation(BaseModel):
    """has_measurement is false exactly when the list is empty."""

    model_config = ConfigDict(extra="forbid")

    has_measurement: bool
    measurements: list[Measurement] = Field(default_factory=list)

    @model_validator(mode="after")
    def _boolean_matches_list(self) -> Annotation:
        if self.has_measurement != bool(self.measurements):
            raise ValueError(
                "has_measurement must be true iff measurements is non-empty"
            )
        return self
