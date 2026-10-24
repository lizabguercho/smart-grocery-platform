"""Tests for the extensible labeling desk (no browser / no network)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.slm_benchmark.annotation_io import write_annotations
from src.slm_benchmark.annotation_schema import AnnotationRow, AnnotationStatus
from src.slm_benchmark.labeling.app import create_app
from src.slm_benchmark.labeling.base import LabelDecision, TaskRegistry
from src.slm_benchmark.labeling.tasks.translation_v2 import TranslationV2Task


def _seed(path: Path) -> None:
    rows = [
        AnnotationRow(
            item_code="7290117906422",
            raw_item_name="אגוז קשיו קלוי ענק 150 גרם",
            is_product=True,
            category="Snacks & Sweets",
            candidate_name_en="Giant Roasted Cashews",
            candidate_quantity=150,
            candidate_unit="g",
            candidate_product_type="cashews",
            annotation_status=AnnotationStatus.UNREVIEWED,
        ),
        AnnotationRow(
            item_code="np-001",
            raw_item_name="דמי משלוח",
            is_product=False,
            annotation_status=AnnotationStatus.UNREVIEWED,
        ),
    ]
    write_annotations(rows, path)


def test_translation_task_accept_and_correct(tmp_path: Path) -> None:
    path = tmp_path / "ann.csv"
    _seed(path)
    task = TranslationV2Task(path)

    first = task.next_item(status="unreviewed")
    assert first is not None
    assert first.item_id == "7290117906422"

    updated = task.apply_decision(
        first.item_id,
        LabelDecision(
            action="accept",
            # UI always posts prefilled form values; Accept must stay "accepted".
            values={
                "name_en": "Giant Roasted Cashews",
                "product_type": "cashews",
                "quantity": 150,
                "unit": "g",
            },
        ),
    )
    assert updated.status == "accepted"
    assert updated.values["name_en"] == "Giant Roasted Cashews"

    corrected = task.apply_decision(
        first.item_id,
        LabelDecision(
            action="correct",
            values={
                "name_en": "Jumbo Roasted Cashews 150 g",
                "product_type": "cashews",
                "variant": "jumbo roasted",
                "quantity": 150,
                "unit": "g",
            },
        ),
    )
    assert corrected.status == "corrected"
    assert corrected.values["name_en"] == "Jumbo Roasted Cashews 150 g"

    fee = task.next_item(status="unreviewed")
    assert fee is not None
    assert fee.item_id == "np-001"
    excluded = task.apply_decision(fee.item_id, LabelDecision(action="exclude", notes="fee"))
    assert excluded.status == "excluded"
    assert task.stats().remaining_unreviewed == 0

    unlabeled = task.apply_decision(
        first.item_id, LabelDecision(action="unlabel")
    )
    assert unlabeled.status == "unreviewed"
    assert unlabeled.values["name_en"] == "Giant Roasted Cashews"  # form prefills candidates

    stats = task.reset_all()
    assert stats.remaining_unreviewed == 2
    assert stats.by_status.get("accepted", 0) == 0


def test_labeling_api_schema_driven(tmp_path: Path) -> None:
    path = tmp_path / "ann.csv"
    _seed(path)
    registry = TaskRegistry()
    registry.register(TranslationV2Task(path))
    client = TestClient(create_app(registry))

    tasks = client.get("/api/tasks").json()
    assert tasks[0]["task_id"] == "translation_v2"

    detail = client.get("/api/tasks/translation_v2").json()
    assert any(field["key"] == "name_en" for field in detail["fields"])

    nxt = client.get("/api/tasks/translation_v2/next").json()
    assert nxt["item_id"] == "7290117906422"

    items = client.get("/api/tasks/translation_v2/items").json()
    assert len(items) == 2
    assert items[0]["item_id"] == "7290117906422"
    assert items[0]["status"] == "unreviewed"
    assert items[1]["status"] == "unreviewed"

    decided = client.post(
        f"/api/tasks/translation_v2/items/{nxt['item_id']}/decision",
        json={"action": "correct", "values": {"name_en": "Jumbo Roasted Cashews 150 g", "quantity": 150, "unit": "g"}},
    ).json()
    assert decided["status"] == "corrected"
    assert decided["values"]["name_en"] == "Jumbo Roasted Cashews 150 g"

    items = client.get("/api/tasks/translation_v2/items").json()
    assert items[0]["status"] == "corrected"

    html = client.get("/").text
    assert "Labeling desk" in html
    assert "queue-list" in html
    assert "dot-accepted" in html

    bad = client.post("/api/tasks/translation_v2/reset", json={"confirm": False})
    assert bad.status_code == 400
    reset = client.post("/api/tasks/translation_v2/reset", json={"confirm": True})
    assert reset.status_code == 200
    assert reset.json()["remaining_unreviewed"] == 2
