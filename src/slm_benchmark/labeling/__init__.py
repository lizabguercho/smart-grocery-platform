"""Extensible local labeling framework.

New labeling jobs register a ``LabelingTask`` implementation. The UI and
HTTP API are schema-driven from each task's field specs, so adding a
future task (e.g. category corrections) does not require rewriting the
frontend.
"""

from __future__ import annotations

from src.slm_benchmark.labeling.base import (
    FieldSpec,
    LabelDecision,
    LabelItem,
    LabelingTask,
    TaskInfo,
    TaskRegistry,
)
from src.slm_benchmark.labeling.registry import default_registry

__all__ = [
    "FieldSpec",
    "LabelDecision",
    "LabelItem",
    "LabelingTask",
    "TaskInfo",
    "TaskRegistry",
    "default_registry",
]
