"""Human annotations as an append-only JSONL log.

One line per save; the latest line for an item is its current state and the
earlier lines are its history. Nothing is ever rewritten, so no gold is lost.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.measurement_extraction.config import GUIDELINE_VERSION, SCHEMA_VERSION
from src.measurement_extraction.schema import Annotation, WorkflowState


def read_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def history(log: list[dict], item_code: str) -> list[dict]:
    return [r for r in log if r["item_code"] == item_code]


def latest(log: list[dict]) -> dict[str, dict]:
    return {r["item_code"]: r for r in log}


def append(
    path: Path,
    item_code: str,
    split: str,
    state: WorkflowState,
    annotation: Annotation | None,
    notes: str | None,
    reason: str | None,
    previous: dict | None,
    annotator: str = "human",
) -> dict:
    """Validate and append one record; correcting a saved item needs a reason."""

    if state is WorkflowState.SAVED and annotation is None:
        raise ValueError("a saved annotation needs a payload")
    if (
        previous
        and previous["state"] == "saved"
        and state is WorkflowState.SAVED
        and not reason
    ):
        raise ValueError("correcting a saved annotation requires a reason")
    record = {
        "item_code": item_code,
        "split": split,
        "state": state.value,
        "annotation": json.loads(annotation.model_dump_json()) if annotation else None,
        "notes": notes,
        "reason": reason,
        "annotator": annotator,
        "revision": (previous["revision"] if previous else 0) + 1,
        "saved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "schema_version": SCHEMA_VERSION,
        "guideline_version": GUIDELINE_VERSION,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
