from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from src.etl.pipeline import Pipeline
from src.etl.protocols import Extractor, Loader, Parser


class FakeExtractor(Extractor):
    def __init__(self, files: list[Path], error: Exception | None = None) -> None:
        self.files = files
        self.error = error
        self.calls = 0

    def extract(self) -> list[Path]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.files


class FakeParser(Parser[str]):
    def __init__(
        self,
        records: Sequence[str],
        error: Exception | None = None,
    ) -> None:
        self.records = records
        self.error = error
        self.calls: list[list[Path]] = []

    def parse(self, files: list[Path]) -> Sequence[str]:
        self.calls.append(files)
        if self.error is not None:
            raise self.error
        return self.records


class FakeLoader(Loader[str]):
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[Sequence[str]] = []

    def load(self, records: Sequence[str]) -> None:
        self.calls.append(records)
        if self.error is not None:
            raise self.error


def test_pipeline_runs_extract_then_parse_then_load() -> None:
    files = [Path("a.gz"), Path("b.gz")]
    extractor = FakeExtractor(files)
    parser = FakeParser(["record-1", "record-2"])
    loader = FakeLoader()
    pipeline = Pipeline(extractor, parser, loader)

    records = pipeline.run()

    assert extractor.calls == 1
    assert parser.calls == [files]
    assert loader.calls == [["record-1", "record-2"]]
    assert list(records) == ["record-1", "record-2"]


def test_pipeline_does_not_parse_when_extract_fails() -> None:
    extractor = FakeExtractor([], error=RuntimeError("extract failed"))
    parser = FakeParser(["unused"])
    loader = FakeLoader()
    pipeline = Pipeline(extractor, parser, loader)

    with pytest.raises(RuntimeError, match="extract failed"):
        pipeline.run()

    assert parser.calls == []
    assert loader.calls == []


def test_pipeline_does_not_load_when_parse_fails() -> None:
    files = [Path("a.gz")]
    extractor = FakeExtractor(files)
    parser = FakeParser([], error=ValueError("parse failed"))
    loader = FakeLoader()
    pipeline = Pipeline(extractor, parser, loader)

    with pytest.raises(ValueError, match="parse failed"):
        pipeline.run()

    assert parser.calls == [files]
    assert loader.calls == []
