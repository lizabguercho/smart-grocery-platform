"""Thin local file server for the annotation page.

It holds no logic: it serves the samples (CSV) and the unit table, and appends
what the human saves to the gold JSONL. Sampling, conversion for scoring and
inference are separate scripts that read and write the same files.

Run: PYTHONPATH=. uv run uvicorn src.measurement_extraction.app:app --port 8765
The page never receives predictions: they stay in research/normalization/predictions.
"""

from __future__ import annotations

import csv
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from src.measurement_extraction import gold_log
from src.measurement_extraction.config import GOLD_PATH, SAMPLES_DIR
from src.measurement_extraction.schema import Annotation, WorkflowState
from src.measurement_extraction.units import registry_json

PAGE = Path(__file__).parent / "static" / "annotate.html"
SPLITS = ("dev", "test")


class SaveRequest(BaseModel):
    state: WorkflowState
    annotation: Annotation | None = None
    notes: str | None = None
    reason: str | None = None


def read_samples(samples_dir: Path, split: str) -> list[dict]:
    path = samples_dir / f"{split}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            {"item_code": r["item_code"], "item_name": r["item_name"]}
            for r in csv.DictReader(handle)
        ]


def create_app(gold_path: Path = GOLD_PATH, samples_dir: Path = SAMPLES_DIR) -> FastAPI:
    app = FastAPI(title="Measurement annotation", docs_url=None, redoc_url=None)

    def view(split: str) -> list[dict]:
        current = gold_log.latest(gold_log.read_log(gold_path))
        out = []
        for sample in read_samples(samples_dir, split):
            saved = current.get(sample["item_code"])
            out.append(
                {
                    **sample,
                    "split": split,
                    "state": saved["state"] if saved else "unreviewed",
                    "revision": saved["revision"] if saved else 0,
                    "notes": saved["notes"] if saved else None,
                    "annotation": saved["annotation"] if saved else None,
                }
            )
        return out

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return PAGE.read_text(encoding="utf-8")

    @app.get("/units.json")
    def units() -> dict:
        return registry_json()

    @app.get("/api/items")
    def items(split: str = "dev") -> list[dict]:
        return view(split)

    @app.put("/api/items/{item_code}")
    def save(item_code: str, request: SaveRequest) -> dict:
        found = next(
            (i for s in SPLITS for i in view(s) if i["item_code"] == item_code), None
        )
        if found is None:
            raise HTTPException(404, "unknown item")
        log = gold_log.read_log(gold_path)
        previous = gold_log.latest(log).get(item_code)
        try:
            gold_log.append(
                gold_path,
                item_code,
                found["split"],
                request.state,
                request.annotation,
                request.notes,
                request.reason,
                previous,
            )
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        return next(i for i in view(found["split"]) if i["item_code"] == item_code)

    @app.post("/api/items/{item_code}/undo")
    def undo(item_code: str) -> dict:
        log = gold_log.read_log(gold_path)
        past = gold_log.history(log, item_code)
        if len(past) < 2:
            raise HTTPException(422, "nothing to undo")
        before, current = past[-2], past[-1]
        gold_log.append(
            gold_path,
            item_code,
            current["split"],
            WorkflowState(before["state"]),
            Annotation.model_validate(before["annotation"])
            if before["annotation"]
            else None,
            before["notes"],
            "undo",
            None,
        )
        return next(i for i in view(current["split"]) if i["item_code"] == item_code)

    @app.get("/api/gold.jsonl", response_class=PlainTextResponse)
    def gold() -> str:
        return gold_path.read_text(encoding="utf-8") if gold_path.exists() else ""

    return app


app = create_app()
