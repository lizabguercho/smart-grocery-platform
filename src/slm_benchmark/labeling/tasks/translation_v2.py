"""Translation-v2 labeling task backed by the annotations CSV."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.slm_benchmark.annotation_io import (
    V2_ANNOTATIONS_CSV,
    load_annotations,
    write_annotations,
)
from src.slm_benchmark.annotation_schema import AnnotationRow, AnnotationStatus
from src.slm_benchmark.labeling.base import (
    FieldSpec,
    FieldType,
    LabelDecision,
    LabelItem,
    LabelItemSummary,
    LabelingTask,
    TaskInfo,
    TaskStats,
)

_GOLD_KEYS = (
    "name_en",
    "brand",
    "product_type",
    "variant",
    "quantity",
    "unit",
    "pack_count",
    "percent",
)


class TranslationV2Task(LabelingTask):
    """Human review of semantic English / SKU gold for the frozen v1 IDs."""

    def __init__(self, annotations_path: Path | None = None) -> None:
        self._path = annotations_path or V2_ANNOTATIONS_CSV
        self._rows: list[AnnotationRow] | None = None
        self._loaded_mtime: float | None = None

    @property
    def info(self) -> TaskInfo:
        return TaskInfo(
            task_id="translation_v2",
            title="Translation gold (v2)",
            description=(
                "Accept or correct natural-English product names and SKU "
                "attributes. Candidates are suggestions only — never auto-gold."
            ),
            version="1",
        )

    def field_specs(self) -> list[FieldSpec]:
        return [
            FieldSpec(
                key="name_en",
                label="English name",
                field_type=FieldType.TEXTAREA,
                required=False,
                candidate_key="name_en",
                help_text="Natural English catalog name (not transliteration).",
            ),
            FieldSpec(
                key="brand",
                label="Brand",
                candidate_key="brand",
            ),
            FieldSpec(
                key="product_type",
                label="Product type",
                candidate_key="product_type",
                help_text="Short type phrase, e.g. cashews, lactose-free milk.",
            ),
            FieldSpec(
                key="variant",
                label="Variant",
                candidate_key="variant",
                help_text="Flavor / form / size descriptor when SKU-relevant.",
            ),
            FieldSpec(
                key="quantity",
                label="Quantity",
                field_type=FieldType.NUMBER,
                candidate_key="quantity",
            ),
            FieldSpec(
                key="unit",
                label="Unit",
                candidate_key="unit",
                help_text="Prefer g, kg, mL, L, units, bags.",
            ),
            FieldSpec(
                key="pack_count",
                label="Pack count",
                field_type=FieldType.NUMBER,
                candidate_key="pack_count",
            ),
            FieldSpec(
                key="percent",
                label="Percent",
                field_type=FieldType.NUMBER,
                candidate_key="percent",
            ),
        ]

    def _load(self) -> list[AnnotationRow]:
        # Reload when annotate_candidates (or another process) updates the CSV.
        mtime = self._path.stat().st_mtime if self._path.exists() else None
        if self._rows is None or mtime != self._loaded_mtime:
            self._rows = load_annotations(self._path)
            self._loaded_mtime = mtime
        return self._rows

    def _save(self) -> None:
        assert self._rows is not None
        write_annotations(self._rows, self._path)
        self._loaded_mtime = self._path.stat().st_mtime if self._path.exists() else None

    def _index(self) -> dict[str, int]:
        return {row.item_code: i for i, row in enumerate(self._load())}

    def stats(self) -> TaskStats:
        rows = self._load()
        by_status: dict[str, int] = {}
        for row in rows:
            key = row.annotation_status.value
            by_status[key] = by_status.get(key, 0) + 1
        return TaskStats(
            task_id=self.info.task_id,
            total=len(rows),
            by_status=by_status,
            remaining_unreviewed=by_status.get("unreviewed", 0),
        )

    def _to_item(self, row: AnnotationRow, *, position: int, total: int) -> LabelItem:
        values = {
            "name_en": row.gold_name_en,
            "brand": row.gold_brand,
            "product_type": row.gold_product_type,
            "variant": row.gold_variant,
            "quantity": row.gold_quantity,
            "unit": row.gold_unit,
            "pack_count": row.gold_pack_count,
            "percent": row.gold_percent,
        }
        # If unreviewed, prefill the form from candidates for faster accept/edit.
        if row.annotation_status == AnnotationStatus.UNREVIEWED:
            values = {
                "name_en": row.candidate_name_en,
                "brand": row.candidate_brand,
                "product_type": row.candidate_product_type,
                "variant": row.candidate_variant,
                "quantity": row.candidate_quantity,
                "unit": row.candidate_unit,
                "pack_count": row.candidate_pack_count,
                "percent": row.candidate_percent,
            }
        candidates = {
            "name_en": row.candidate_name_en,
            "brand": row.candidate_brand,
            "product_type": row.candidate_product_type,
            "variant": row.candidate_variant,
            "quantity": row.candidate_quantity,
            "unit": row.candidate_unit,
            "pack_count": row.candidate_pack_count,
            "percent": row.candidate_percent,
        }
        return LabelItem(
            item_id=row.item_code,
            task_id=self.info.task_id,
            status=row.annotation_status.value,
            title=row.raw_item_name,
            subtitle=f"item_code={row.item_code}",
            meta={
                "is_product": row.is_product,
                "category": row.category,
                "subcategory": row.subcategory,
                "manufacture_name": row.manufacture_name,
                "slice_tags": row.slice_tags,
                "annotator_model_id": row.annotator_model_id,
            },
            values=values,
            candidates=candidates,
            notes=row.annotation_notes,
            position=position,
            total=total,
        )

    def list_items(self) -> list[LabelItemSummary]:
        rows = self._load()
        return [
            LabelItemSummary(
                item_id=row.item_code,
                status=row.annotation_status.value,
                title=row.raw_item_name,
                subtitle=row.item_code,
                position=i + 1,
            )
            for i, row in enumerate(rows)
        ]

    def get_item(self, item_id: str) -> LabelItem | None:
        rows = self._load()
        idx = self._index().get(item_id)
        if idx is None:
            return None
        return self._to_item(rows[idx], position=idx + 1, total=len(rows))

    def next_item(
        self,
        *,
        status: str | None = "unreviewed",
        after_item_id: str | None = None,
    ) -> LabelItem | None:
        rows = self._load()
        start = 0
        if after_item_id is not None:
            idx = self._index().get(after_item_id)
            if idx is not None:
                start = idx + 1
        for offset, row in enumerate(rows[start:], start=start):
            if status is None or row.annotation_status.value == status:
                return self._to_item(row, position=offset + 1, total=len(rows))
        # Wrap around for convenience.
        if start > 0:
            for offset, row in enumerate(rows[:start]):
                if status is None or row.annotation_status.value == status:
                    return self._to_item(row, position=offset + 1, total=len(rows))
        return None

    def _parse_optional_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        return float(value)

    def _parse_optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def apply_decision(self, item_id: str, decision: LabelDecision) -> LabelItem:
        rows = self._load()
        idx = self._index().get(item_id)
        if idx is None:
            raise KeyError(f"Unknown item_id: {item_id}")
        row = rows[idx]

        if decision.action == "skip":
            if decision.notes:
                row.annotation_notes = decision.notes
                self._save()
            return self._to_item(row, position=idx + 1, total=len(rows))

        if decision.action == "exclude":
            row.annotation_status = AnnotationStatus.EXCLUDED
            if decision.notes:
                row.annotation_notes = decision.notes
            self._save()
            return self._to_item(row, position=idx + 1, total=len(rows))

        if decision.action == "accept":
            if not row.is_product:
                row.clear_gold_for_non_product()
                row.annotation_status = AnnotationStatus.ACCEPTED
            else:
                # Accept always means "candidates become gold".
                # Form values are ignored here — edits go through "correct".
                # (The UI prefills the form from candidates, so treating
                # non-empty submits as corrections wrongly marked Accept.)
                row.accept_candidates()
            if decision.notes:
                row.annotation_notes = decision.notes
            self._save()
            return self._to_item(row, position=idx + 1, total=len(rows))

        if decision.action == "correct":
            self._write_gold_from_values(row, decision.values)
            if not row.is_product:
                row.clear_gold_for_non_product()
            row.annotation_status = AnnotationStatus.CORRECTED
            if decision.notes:
                row.annotation_notes = decision.notes
            self._save()
            return self._to_item(row, position=idx + 1, total=len(rows))

        if decision.action == "unlabel":
            self._clear_human_label(row)
            if decision.notes:
                row.annotation_notes = decision.notes
            self._save()
            return self._to_item(row, position=idx + 1, total=len(rows))

        raise ValueError(f"Unsupported action: {decision.action}")

    def reset_all(self) -> TaskStats:
        rows = self._load()
        for row in rows:
            self._clear_human_label(row)
        self._save()
        return self.stats()

    def _clear_human_label(self, row: AnnotationRow) -> None:
        """Drop gold / status; keep Hebrew source and LLM candidates."""

        row.clear_gold_for_non_product()
        row.annotation_status = AnnotationStatus.UNREVIEWED
        row.annotation_notes = ""

    def _write_gold_from_values(self, row: AnnotationRow, values: dict[str, Any]) -> None:
        row.gold_name_en = self._parse_optional_str(values.get("name_en"))
        row.gold_brand = self._parse_optional_str(values.get("brand"))
        row.gold_product_type = self._parse_optional_str(values.get("product_type"))
        row.gold_variant = self._parse_optional_str(values.get("variant"))
        row.gold_quantity = self._parse_optional_float(values.get("quantity"))
        row.gold_unit = self._parse_optional_str(values.get("unit"))
        row.gold_pack_count = self._parse_optional_float(values.get("pack_count"))
        row.gold_percent = self._parse_optional_float(values.get("percent"))
