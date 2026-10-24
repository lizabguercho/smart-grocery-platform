"""Core types for pluggable labeling tasks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    BOOL = "bool"
    SELECT = "select"
    TEXTAREA = "textarea"


class FieldSpec(BaseModel):
    """One editable or display field rendered by the labeling UI."""

    key: str
    label: str
    field_type: FieldType = FieldType.TEXT
    editable: bool = True
    required: bool = False
    options: list[str] = Field(default_factory=list)
    help_text: str = ""
    # Optional parallel candidate value key on the item payload.
    candidate_key: str | None = None


class TaskInfo(BaseModel):
    task_id: str
    title: str
    description: str
    version: str = "1"


class LabelItem(BaseModel):
    """One unit of work returned to the UI."""

    item_id: str
    task_id: str
    status: str
    title: str
    subtitle: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)
    # field_key -> current gold (or draft) value
    values: dict[str, Any] = Field(default_factory=dict)
    # field_key -> candidate suggestion
    candidates: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    position: int | None = None
    total: int | None = None


class LabelDecision(BaseModel):
    """Human decision submitted for one item."""

    action: Literal["accept", "correct", "exclude", "skip", "unlabel"]
    values: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class ResetRequest(BaseModel):
    """Destructive reset of all labels for a task."""

    confirm: bool = False


class TaskStats(BaseModel):
    task_id: str
    total: int
    by_status: dict[str, int]
    remaining_unreviewed: int


class LabelItemSummary(BaseModel):
    """Compact row for the labeling sidebar / queue list."""

    item_id: str
    status: str
    title: str
    subtitle: str = ""
    position: int


class LabelingTask(ABC):
    """Contract every labeling job must implement."""

    @property
    @abstractmethod
    def info(self) -> TaskInfo: ...

    @abstractmethod
    def field_specs(self) -> list[FieldSpec]: ...

    @abstractmethod
    def stats(self) -> TaskStats: ...

    @abstractmethod
    def list_items(self) -> list[LabelItemSummary]: ...

    @abstractmethod
    def get_item(self, item_id: str) -> LabelItem | None: ...

    @abstractmethod
    def next_item(
        self,
        *,
        status: str | None = "unreviewed",
        after_item_id: str | None = None,
    ) -> LabelItem | None: ...

    @abstractmethod
    def apply_decision(self, item_id: str, decision: LabelDecision) -> LabelItem: ...

    @abstractmethod
    def reset_all(self) -> TaskStats:
        """Clear all human labels; keep source rows and candidates."""
        ...


class TaskRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, LabelingTask] = {}

    def register(self, task: LabelingTask) -> None:
        task_id = task.info.task_id
        if task_id in self._tasks:
            raise ValueError(f"Task already registered: {task_id}")
        self._tasks[task_id] = task

    def get(self, task_id: str) -> LabelingTask:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise KeyError(f"Unknown labeling task: {task_id}") from exc

    def list_tasks(self) -> list[TaskInfo]:
        return [task.info for task in self._tasks.values()]
