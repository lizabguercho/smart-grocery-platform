"""Extract the prompt text from a source file and fingerprint it.

Shared by the registry and by the prompt-review skill so both agree on what
"the prompt" is and when it changed.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path


def _string_value(node: ast.expr | None) -> str | None:
    """A string literal, optionally followed by .strip(), as the prompt constants are written."""

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (
        isinstance(node, ast.Call)
        and not node.args
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "strip"
    ):
        inner = _string_value(node.func.value)
        return None if inner is None else inner.strip()
    return None


def extract_prompt(path: Path, symbol: str | None = None) -> tuple[str, int, str]:
    """Return (text, first_line_in_file, symbol).

    .py: the module-level string named `symbol`, else the longest one whose
    name contains PROMPT. Other files: the whole text.
    """

    raw = path.read_text(encoding="utf-8")
    if path.suffix != ".py":
        return raw, 1, "text"
    best = None
    for node in ast.parse(raw).body:
        targets: list[str] = []
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        value = _string_value(getattr(node, "value", None))
        if value is None:
            continue
        for name in targets:
            wanted = name == symbol if symbol else "PROMPT" in name.upper()
            if wanted and (best is None or len(value) > len(best[0])):
                best = (value, node.value.lineno, name)
    if best is None:
        raise ValueError(f"{path}: no prompt string found (symbol={symbol!r})")
    return best


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
