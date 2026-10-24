"""Built-in labeling task registrations."""

from __future__ import annotations

from src.slm_benchmark.labeling.base import TaskRegistry
from src.slm_benchmark.labeling.tasks.translation_v2 import TranslationV2Task


def default_registry() -> TaskRegistry:
    registry = TaskRegistry()
    registry.register(TranslationV2Task())
    return registry
