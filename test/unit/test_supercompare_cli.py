from __future__ import annotations

from pathlib import Path

import pytest

from src.product_classification.supercompare import cli
from src.product_classification.supercompare.models import CrawlSummary


def test_parse_args_uses_resumable_defaults() -> None:
    args = cli.parse_args([])

    assert args.city == "tel-aviv"
    assert args.resume is True
    assert args.category is None
    assert args.subcategory == []


def test_config_from_args_accepts_category_slice_and_custom_paths(
    tmp_path: Path,
) -> None:
    args = cli.parse_args(
        [
            "--category",
            "dairy-and-eggs",
            "--subcategory",
            "milk",
            "--no-resume",
            "--raw-dir",
            str(tmp_path / "raw"),
            "--output",
            str(tmp_path / "products.csv"),
        ]
    )

    config = cli.config_from_args(args)

    assert config.category_slug == "dairy-and-eggs"
    assert config.subcategory_slugs == ("milk",)
    assert config.resume is False
    assert config.raw_dir == tmp_path / "raw"


def test_config_rejects_subcategory_without_category() -> None:
    args = cli.parse_args(["--subcategory", "milk"])

    with pytest.raises(ValueError, match="requires a category"):
        cli.config_from_args(args)


def test_main_runs_crawler_and_returns_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    summary = CrawlSummary(
        categories=1,
        subcategories=1,
        expected_pages=1,
        downloaded_pages=1,
        cached_pages=0,
        products=1,
        failures=(),
        products_path=tmp_path / "products.csv",
    )
    calls: dict[str, bool] = {}

    class FakeClient:
        def __init__(self, _config) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            pass

    class FakeCrawler:
        def __init__(self, _config, _client, _store) -> None:
            pass

        def run(self) -> CrawlSummary:
            calls["ran"] = True
            return summary

    monkeypatch.setattr(cli, "configure_logging", lambda *_args: None)
    monkeypatch.setattr(cli, "SuperCompareClient", FakeClient)
    monkeypatch.setattr(cli, "SuperCompareCrawler", FakeCrawler)

    exit_code = cli.main(
        [
            "--log-file",
            str(tmp_path / "crawler.log"),
            "--output",
            str(tmp_path / "products.csv"),
        ]
    )

    assert exit_code == 0
    assert calls == {"ran": True}
