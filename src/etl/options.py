from dataclasses import dataclass

from src.etl.constants import DEFAULT_MAX_FILES, DEFAULT_MAX_PAGES


@dataclass(frozen=True)
class PipelineOptions:
    download: bool = True
    max_files: int | None = DEFAULT_MAX_FILES
    max_pages: int | None = DEFAULT_MAX_PAGES
