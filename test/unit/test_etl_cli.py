from __future__ import annotations

import pytest

from src.etl.cli import main, options_from_args, parse_args
from src.etl.constants import DEFAULT_MAX_FILES, DEFAULT_MAX_PAGES
from src.etl.enums import Chain, ExtractType
from src.etl.options import PipelineOptions


def test_parse_args_requires_chain() -> None:
    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_defaults() -> None:
    args = parse_args(["--chain", "shufersal"])

    assert args.chain == Chain.SHUFERSAL.value
    assert args.extract == ExtractType.PRICES_FULL.value
    assert args.max_files == DEFAULT_MAX_FILES
    assert args.max_pages == DEFAULT_MAX_PAGES
    assert args.full is False
    assert args.download is True


def test_parse_args_accepts_extract_type_max_pages_and_no_download() -> None:
    args = parse_args(
        [
            "--chain",
            "rami_levy",
            "--extract",
            "stores",
            "--max-files",
            "8",
            "--max-pages",
            "4",
            "--no-download",
        ]
    )

    assert args.chain == Chain.RAMI_LEVY.value
    assert args.extract == ExtractType.STORES.value
    assert args.max_files == 8
    assert args.max_pages == 4
    assert args.download is False


def test_options_from_args_full_clears_limits() -> None:
    args = parse_args(
        [
            "--chain",
            "victory",
            "--max-files",
            "9",
            "--max-pages",
            "6",
            "--full",
        ]
    )

    options = options_from_args(args)

    assert options == PipelineOptions(
        download=True,
        max_files=None,
        max_pages=None,
    )


def test_main_creates_pipeline_from_cli_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    created: dict[str, object] = {}

    class FakePipeline:
        def run(self) -> list[str]:
            created["ran"] = True
            return []

    class FakeFactory:
        @staticmethod
        def create(chain, extract_type, options):
            created["chain"] = chain
            created["extract_type"] = extract_type
            created["options"] = options
            return FakePipeline()

    monkeypatch.setattr("src.etl.cli.PipelineFactory", FakeFactory)

    main(
        [
            "--chain",
            "shufersal",
            "--extract",
            "prices_full",
            "--max-pages",
            "5",
            "--max-files",
            "2",
        ]
    )

    assert created["chain"] is Chain.SHUFERSAL
    assert created["extract_type"] is ExtractType.PRICES_FULL
    assert created["options"] == PipelineOptions(
        download=True,
        max_files=2,
        max_pages=5,
    )
    assert created["ran"] is True
