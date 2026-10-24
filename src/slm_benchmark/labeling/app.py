"""FastAPI app for the local labeling desk."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from src.slm_benchmark.labeling.base import LabelDecision, ResetRequest, TaskRegistry
from src.slm_benchmark.labeling.registry import default_registry
from src.slm_benchmark.labeling.ui import LABELING_UI_HTML

API_TITLE = "Smart Grocery labeling desk"
API_VERSION = "0.1.0"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def create_app(registry: TaskRegistry | None = None) -> FastAPI:
    tasks = registry or default_registry()
    app = FastAPI(title=API_TITLE, version=API_VERSION)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return LABELING_UI_HTML

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "tasks": [t.task_id for t in tasks.list_tasks()]}

    @app.get("/api/tasks")
    def list_tasks() -> list[dict]:
        return [info.model_dump() for info in tasks.list_tasks()]

    @app.get("/api/tasks/{task_id}")
    def task_detail(task_id: str) -> dict:
        try:
            task = tasks.get(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            **task.info.model_dump(),
            "fields": [spec.model_dump() for spec in task.field_specs()],
        }

    @app.get("/api/tasks/{task_id}/stats")
    def task_stats(task_id: str) -> dict:
        try:
            task = tasks.get(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return task.stats().model_dump()

    @app.get("/api/tasks/{task_id}/items")
    def list_items(task_id: str) -> list[dict]:
        try:
            task = tasks.get(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return [item.model_dump() for item in task.list_items()]

    @app.get("/api/tasks/{task_id}/next")
    def next_item(
        task_id: str,
        status: str | None = Query(default="unreviewed"),
        after: str | None = Query(default=None),
    ) -> dict | None:
        try:
            task = tasks.get(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        # Empty string means "all statuses".
        status_filter = status if status else None
        item = task.next_item(status=status_filter, after_item_id=after)
        return None if item is None else item.model_dump()

    @app.get("/api/tasks/{task_id}/items/{item_id}")
    def get_item(task_id: str, item_id: str) -> dict:
        try:
            task = tasks.get(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        item = task.get_item(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Unknown item: {item_id}")
        return item.model_dump()

    @app.post("/api/tasks/{task_id}/items/{item_id}/decision")
    def decide(task_id: str, item_id: str, decision: LabelDecision) -> dict:
        try:
            task = tasks.get(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        try:
            item = task.apply_decision(item_id, decision)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return item.model_dump()

    @app.post("/api/tasks/{task_id}/reset")
    def reset_task(task_id: str, body: ResetRequest) -> dict:
        try:
            task = tasks.get(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if not body.confirm:
            raise HTTPException(
                status_code=400,
                detail="Reset requires confirm=true after an explicit UI confirmation.",
            )
        return task.reset_all().model_dump()

    return app
