import importlib.util
from pathlib import Path

import pytest

from src.prompt_registry.extract import extract_prompt, fingerprint
from src.prompt_registry.reviews import collect, render_status, state

PROMPT = 'SYSTEM_PROMPT = """\\\nDo the task.\n"""\nOTHER = "x"\n'
HEADER = (
    "# Prompt reviews — t\nCategory: preprocessing/x\nPrompt: p.py\nModel: m\n"
    "Owner: o\nPurpose: p\nNext step: n\n"
)


def _repo(tmp_path: Path, entry: str, sha: str) -> tuple[Path, Path]:
    (tmp_path / "p.py").write_text(PROMPT, encoding="utf-8")
    folder = tmp_path / "docs" / "prompts" / "preprocessing" / "t"
    folder.mkdir(parents=True)
    body = HEADER + entry.format(sha=sha)
    (folder / "REVIEWS.md").write_text(body, encoding="utf-8")
    return tmp_path, tmp_path / "docs" / "prompts"


ENTRY = (
    "\n## 2026-11-14 — actions: CLARIFY, SPLIT — validity: valid — tier: small — prompt-sha: {sha}\n"
    "- Load: K=5 band 6/10 -> within\n"
    "- Dimensions: load=ok coherence=fix ambiguity=watch structure=ok efficiency=ok hygiene=ok\n"
)


def test_review_matches_current_prompt_then_goes_stale(tmp_path):
    text, _, name = extract_prompt(_make(tmp_path))
    assert name == "SYSTEM_PROMPT"
    root, prompts = _repo(tmp_path, ENTRY, fingerprint(text))
    record = collect(prompts, root)[0]
    assert state(record) == "action needed" and record.last.k == 5
    (root / "p.py").write_text(PROMPT.replace("Do", "Please do"), encoding="utf-8")
    assert state(collect(prompts, root)[0]) == "changed since review"
    assert "changed since review" in render_status(collect(prompts, root))


def _make(tmp_path: Path) -> Path:
    path = tmp_path / "p.py"
    path.write_text(PROMPT, encoding="utf-8")
    return path


def test_malformed_dimensions_rejected(tmp_path):
    bad = ENTRY.replace("load=ok ", "")
    root, prompts = _repo(tmp_path, bad, "0" * 12)
    with pytest.raises(ValueError, match="Dimensions"):
        collect(prompts, root)


def test_actions_are_independent_and_validated(tmp_path):
    import pytest as _p

    root, prompts = _repo(
        tmp_path, ENTRY.replace("CLARIFY, SPLIT", "NONE, SPLIT"), "0" * 12
    )
    with _p.raises(ValueError, match="NONE"):
        collect(prompts, root)


def test_unreviewed_prompt_is_listed(tmp_path):
    root, prompts = _repo(tmp_path, "", "")
    assert state(collect(prompts, root)[0]) == "unreviewed"


def test_skill_script_agrees_with_registry_on_the_prompt():
    path = Path(".claude/skills/prompt-review/scripts/prompt_metrics.py")
    spec = importlib.util.spec_from_file_location("pm", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = Path("src/measurement_extraction/prompts.py")
    assert module.extract_text(target)[0] == extract_prompt(target)[0]


def test_consistency_metrics_and_diagnosis():
    from src.prompt_registry.consistency import (
        Reading,
        agreement,
        diagnose,
        field_consistency,
        prompt_spread,
    )

    assert agreement(["a", "a", "b", "a"]) == 0.75
    fc = field_consistency(
        {"i1": [{"u": "g"}, {"u": "g"}], "i2": [{"u": "g"}, {"u": "<failed>"}]}
    )
    assert fc["u"]["agreement"] == 0.75 and fc["u"]["unstable_items"] == 1
    assert prompt_spread({"a": 0.8, "b": 0.7})["range"] == pytest.approx(0.1)
    cap = diagnose(Reading(0.7, 0.6), Reading(0.95, 0.9))
    assert cap[0].action == "SPLIT / MOVE-TO-CODE"
    amb = diagnose(Reading(0.7, 0.6), Reading(0.7, 0.7))
    assert amb[0].action == "CLARIFY"
    wrong = diagnose(Reading(0.97, 0.6))
    assert wrong[0].action == "FIX-COHERENCE"
