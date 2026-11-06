"""Changelog parsing, validation and status rendering."""

from __future__ import annotations

import pytest

from src.model_lifecycle.changelog import collect, parse_changelog, render_status

GOOD = """# Changelog — demo
Owner: sam
Task: demo task
Next step: tune prompt

## 0.2.0 — 2026-11-02 — stage: prompt-engineering
- Change: new prompt

## 0.1.0 — 2026-11-01 — stage: error-analysis
- Change: baseline
"""


def _write(tmp_path, text, name="demo"):
    folder = tmp_path / "docs" / "models" / name
    folder.mkdir(parents=True)
    path = folder / "CHANGELOG.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_newest_entry_defines_status(tmp_path) -> None:
    status = parse_changelog("demo", _write(tmp_path, GOOD), tmp_path)
    assert (status.version, status.stage, status.entries) == (
        "0.2.0",
        "prompt-engineering",
        2,
    )


def test_empty_optional_header_does_not_swallow_next_line(tmp_path) -> None:
    text = GOOD.replace("Next step:", "Depends on:\nNext step:")
    status = parse_changelog("demo", _write(tmp_path, text), tmp_path)
    assert status.depends_on == "" and status.next_step == "tune prompt"


@pytest.mark.parametrize(
    "bad",
    [
        GOOD.replace("Owner: sam\n", ""),
        GOOD.replace("stage: prompt-engineering", "stage: vibes"),
        GOOD.replace("0.2.0", "0.0.5"),
        "# Changelog\nOwner: a\nTask: b\nNext step: c\n",
    ],
)
def test_malformed_changelogs_are_rejected(tmp_path, bad) -> None:
    with pytest.raises(ValueError):
        parse_changelog("demo", _write(tmp_path, bad), tmp_path)


def test_rendered_status_lists_every_model(tmp_path) -> None:
    _write(tmp_path, GOOD, "a-model")
    _write(tmp_path, GOOD.replace("0.2.0", "0.3.0"), "b-model")
    text = render_status(collect(tmp_path / "docs" / "models", tmp_path))
    assert (
        "`a-model`" in text
        and "`b-model`" in text
        and "0.3.0" in text
        and "GENERATED" in text
    )
