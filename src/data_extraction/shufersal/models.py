"""Compatibility re-exports for Shufersal imports.

Prefer importing from ``src.data_extraction.models`` directly.
"""

from src.data_extraction.models import FileMetadata, PriceFullProduct

__all__ = ["FileMetadata", "PriceFullProduct"]
