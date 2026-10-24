"""Annotation / gold schema for SLM benchmark v2 translation evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, field_validator

ANNOTATION_STATUSES = ("unreviewed", "accepted", "corrected", "excluded")


class AnnotationStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    EXCLUDED = "excluded"


class CandidateSkuFields(BaseModel):
    """Structured SKU attributes produced by the annotation assistant."""

    name_en: str | None = None
    brand: str | None = None
    product_type: str | None = None
    variant: str | None = None
    quantity: float | None = None
    unit: str | None = None
    pack_count: float | None = None
    percent: float | None = None

    @field_validator(
        "name_en",
        "brand",
        "product_type",
        "variant",
        "unit",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class AnnotationRow(BaseModel):
    """One v2 annotation workspace row (candidate + optional gold)."""

    item_code: str
    raw_item_name: str
    is_product: bool
    category: str | None = None
    subcategory: str | None = None
    manufacture_name: str | None = None
    slice_tags: str = ""

    candidate_name_en: str | None = None
    candidate_brand: str | None = None
    candidate_product_type: str | None = None
    candidate_variant: str | None = None
    candidate_quantity: float | None = None
    candidate_unit: str | None = None
    candidate_pack_count: float | None = None
    candidate_percent: float | None = None

    gold_name_en: str | None = None
    gold_brand: str | None = None
    gold_product_type: str | None = None
    gold_variant: str | None = None
    gold_quantity: float | None = None
    gold_unit: str | None = None
    gold_pack_count: float | None = None
    gold_percent: float | None = None

    annotation_status: AnnotationStatus = AnnotationStatus.UNREVIEWED
    annotation_notes: str = ""
    annotator_model_id: str = ""
    annotated_at: str = ""

    def apply_candidates(self, fields: CandidateSkuFields, model_id: str) -> None:
        self.candidate_name_en = fields.name_en
        self.candidate_brand = fields.brand
        self.candidate_product_type = fields.product_type
        self.candidate_variant = fields.variant
        self.candidate_quantity = fields.quantity
        self.candidate_unit = fields.unit
        self.candidate_pack_count = fields.pack_count
        self.candidate_percent = fields.percent
        self.annotator_model_id = model_id
        self.annotated_at = datetime.now(timezone.utc).isoformat()

    def accept_candidates(self) -> None:
        """Copy candidates into gold (human accept). Never call automatically."""

        self.gold_name_en = self.candidate_name_en
        self.gold_brand = self.candidate_brand
        self.gold_product_type = self.candidate_product_type
        self.gold_variant = self.candidate_variant
        self.gold_quantity = self.candidate_quantity
        self.gold_unit = self.candidate_unit
        self.gold_pack_count = self.candidate_pack_count
        self.gold_percent = self.candidate_percent
        self.annotation_status = AnnotationStatus.ACCEPTED

    def clear_gold_for_non_product(self) -> None:
        self.gold_name_en = None
        self.gold_brand = None
        self.gold_product_type = None
        self.gold_variant = None
        self.gold_quantity = None
        self.gold_unit = None
        self.gold_pack_count = None
        self.gold_percent = None


ANNOTATION_CSV_FIELDS: tuple[str, ...] = (
    "item_code",
    "raw_item_name",
    "is_product",
    "category",
    "subcategory",
    "manufacture_name",
    "slice_tags",
    "candidate_name_en",
    "candidate_brand",
    "candidate_product_type",
    "candidate_variant",
    "candidate_quantity",
    "candidate_unit",
    "candidate_pack_count",
    "candidate_percent",
    "gold_name_en",
    "gold_brand",
    "gold_product_type",
    "gold_variant",
    "gold_quantity",
    "gold_unit",
    "gold_pack_count",
    "gold_percent",
    "annotation_status",
    "annotation_notes",
    "annotator_model_id",
    "annotated_at",
)

GOLD_CSV_FIELDS: tuple[str, ...] = (
    "benchmark_version",
    "item_code",
    "raw_item_name",
    "is_product",
    "category",
    "subcategory",
    "manufacture_name",
    "slice_tags",
    "gold_name_en",
    "gold_brand",
    "gold_product_type",
    "gold_variant",
    "gold_quantity",
    "gold_unit",
    "gold_pack_count",
    "gold_percent",
    "annotation_status",
    "annotation_notes",
)


def _opt_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return float(text)


def _opt_str(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def annotation_row_from_dict(raw: dict[str, str]) -> AnnotationRow:
    status = (raw.get("annotation_status") or "unreviewed").strip() or "unreviewed"
    return AnnotationRow(
        item_code=str(raw["item_code"]).strip(),
        raw_item_name=raw["raw_item_name"],
        is_product=str(raw.get("is_product", "")).strip().lower()
        in {"1", "true", "yes"},
        category=_opt_str(raw.get("category")),
        subcategory=_opt_str(raw.get("subcategory")),
        manufacture_name=_opt_str(raw.get("manufacture_name")),
        slice_tags=(raw.get("slice_tags") or "").strip(),
        candidate_name_en=_opt_str(raw.get("candidate_name_en")),
        candidate_brand=_opt_str(raw.get("candidate_brand")),
        candidate_product_type=_opt_str(raw.get("candidate_product_type")),
        candidate_variant=_opt_str(raw.get("candidate_variant")),
        candidate_quantity=_opt_float(raw.get("candidate_quantity")),
        candidate_unit=_opt_str(raw.get("candidate_unit")),
        candidate_pack_count=_opt_float(raw.get("candidate_pack_count")),
        candidate_percent=_opt_float(raw.get("candidate_percent")),
        gold_name_en=_opt_str(raw.get("gold_name_en")),
        gold_brand=_opt_str(raw.get("gold_brand")),
        gold_product_type=_opt_str(raw.get("gold_product_type")),
        gold_variant=_opt_str(raw.get("gold_variant")),
        gold_quantity=_opt_float(raw.get("gold_quantity")),
        gold_unit=_opt_str(raw.get("gold_unit")),
        gold_pack_count=_opt_float(raw.get("gold_pack_count")),
        gold_percent=_opt_float(raw.get("gold_percent")),
        annotation_status=AnnotationStatus(status),
        annotation_notes=(raw.get("annotation_notes") or "").strip(),
        annotator_model_id=(raw.get("annotator_model_id") or "").strip(),
        annotated_at=(raw.get("annotated_at") or "").strip(),
    )


def annotation_row_to_dict(row: AnnotationRow) -> dict[str, Any]:
    data = row.model_dump()
    data["annotation_status"] = row.annotation_status.value
    data["is_product"] = row.is_product
    for key in (
        "candidate_quantity",
        "candidate_pack_count",
        "candidate_percent",
        "gold_quantity",
        "gold_pack_count",
        "gold_percent",
    ):
        value = data[key]
        data[key] = "" if value is None else value
    for key, value in list(data.items()):
        if value is None:
            data[key] = ""
    return data
