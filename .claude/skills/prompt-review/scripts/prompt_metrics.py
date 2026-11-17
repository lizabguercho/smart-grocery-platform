#!/usr/bin/env python3
"""Deterministic measurements of a prompt file. Stdlib only; prints JSON.

  python3 prompt_metrics.py PROMPT_FILE [--corpus data.csv ...] [--tier small|mid|frontier]

PROMPT_FILE: .py (the longest module-level string whose name contains PROMPT),
or any text/markdown file. Line numbers in the output are relative to the
extracted text; add `line_offset` to get file lines.

These are counts, not verdicts. The skill's rubric turns them into findings.
"""

from __future__ import annotations

import argparse
import ast
import csv
import difflib
import json
import re
import sys
from pathlib import Path

VAGUE = [
    "relevant",
    "appropriate",
    "plausible",
    "plausibly",
    "reasonable",
    "reasonably",
    "similar",
    "etc",
    "and so on",
    "if needed",
    "when necessary",
    "as needed",
    "good",
    "proper",
    "properly",
    "important",
    "significant",
    "clear",
    "obvious",
    "likely",
    "probably",
    "usually",
    "typically",
    "roughly",
    "approximately",
    "may be",
    "some",
    "several",
    "a few",
    "try to",
    "if possible",
    "where possible",
    "best",
]
COMPUTE = [
    "count",
    "convert",
    "calculate",
    "compute",
    "sum",
    "multiply",
    "divide",
    "estimate",
    "compare",
    "rank",
    "sort",
    "average",
    "round",
    "total",
    "translate",
]
STRICT = [
    "never",
    "must",
    "always",
    "only",
    "exactly",
    "do not",
    "don't",
    "not ",
    "no ",
]
COND = ["if ", "when ", "unless", "otherwise", "only if", "only when", "except", "else"]
TIERS = {  # constraint-load bands: (comfortable, risky); heuristics, see references/rubric.md
    "small": (6, 10),
    "mid": (10, 16),
    "frontier": (16, 28),
}


def extract_text(path: Path) -> tuple[str, int, str]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix != ".py":
        return raw, 1, "text"
    best = None
    for node in ast.parse(raw).body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        value = getattr(node, "value", None)
        if (
            any("PROMPT" in t.upper() for t in targets)
            and isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and (best is None or len(value.value) > len(best[0]))
        ):
            best = (value.value, value.lineno, targets[0])
    if best is None:
        return raw, 1, "whole file (no PROMPT string found)"
    return best[0], best[1], best[2]


def words(text: str) -> list[str]:
    return re.findall(r"[\w֐-׿]+", text.lower())


def count_terms(lines: list[str], terms: list[str]) -> dict:
    out: dict[str, list[int]] = {}
    for i, line in enumerate(lines, 1):
        low = f" {line.lower()} "
        for t in terms:
            if re.search(rf"(?<![\w]){re.escape(t.strip())}(?![\w])", low):
                out.setdefault(t.strip(), []).append(i)
    return out


def rule_units(lines: list[str]) -> list[tuple[int, str]]:
    units = []
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if re.match(r"^([-*•]|\d+[.)])\s+\S", s):
            units.append((i, s))
    return units


def schema_fields(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r'"([a-z_][a-z0-9_]*)"\s*:', text)))


def hebrew_or_quoted_literals(text: str) -> list[str]:
    he = re.findall(r"[֐-׿][֐-׿\"'׳״`.]*", text)
    return list(dict.fromkeys(he))


def corpus_overlap(text: str, paths: list[str]) -> dict:
    """Leakage check: prompt word 3-grams and rare literals that occur in corpus rows."""
    rows: list[str] = []
    for p in paths:
        with open(p, encoding="utf-8", newline="") as fh:
            for r in csv.reader(fh):
                rows += [c for c in r if c and not c.isdigit()]
    pw = words(text)
    grams = {" ".join(pw[i : i + 3]) for i in range(len(pw) - 2)}
    hits_g = [g for g in grams if any(g in " ".join(words(r)) for r in rows)]
    literals = [w for w in hebrew_or_quoted_literals(text) if len(w) >= 3]
    hits_l = sorted({w for w in literals if any(w in r for r in rows)})
    return {
        "rows": len(rows),
        "ngram3_hits": sorted(hits_g)[:20],
        "literal_hits": hits_l[:40],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--corpus", nargs="*", default=[])
    ap.add_argument("--tier", choices=TIERS, default="small")
    a = ap.parse_args()
    text, offset, source = extract_text(Path(a.file))
    lines = text.splitlines()
    units = rule_units(lines)
    fields = schema_fields(text)
    sentences = [
        s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if len(s.strip()) > 25
    ]
    dups = []
    for i, s in enumerate(sentences):
        for t in sentences[i + 1 :]:
            if difflib.SequenceMatcher(None, s.lower(), t.lower()).ratio() > 0.75:
                dups.append([s[:80], t[:80]])
    strict = count_terms(lines, STRICT)
    n = len(lines)
    middle = range(n // 3 + 1, 2 * n // 3 + 1)
    strict_mid = sorted({ln for v in strict.values() for ln in v if ln in middle})
    quoted_values = set(re.findall(r'"([a-z0-9_]+)"', text))
    mentioned_not_in_schema = sorted(
        {
            m
            for m in re.findall(r"\b([a-z]+(?:_[a-z]+)+)\b", text)
            if m not in fields and m not in quoted_values and "_" in m
        }
    )
    k = len(units)
    low, high = TIERS[a.tier]
    out = {
        "file": a.file,
        "source": source,
        "line_offset": offset,
        "chars": len(text),
        "est_tokens": round(
            len(text) / 3.2
        ),  # rough; Hebrew/JSON tokenise heavier than English
        "lines": n,
        "has_examples": bool(
            re.search(r"\b(e\.g\.|for example|example:|i\.e\.)", text, re.IGNORECASE)
        ),
        "example_markers": count_terms(
            lines, ["e.g.", "for example", "example", "such as"]
        ),
        "literal_non_ascii_tokens": hebrew_or_quoted_literals(text)[:30],
        "constraint_units": k,
        "constraint_lines": [i for i, _ in units],
        "schema_fields": fields,
        "n_schema_fields": len(fields),
        "snake_case_terms_not_in_schema": mentioned_not_in_schema,
        "conditionals": count_terms(lines, COND),
        "n_conditional_lines": len(
            {ln for v in count_terms(lines, COND).values() for ln in v}
        ),
        "strict_terms": {t: len(v) for t, v in strict.items()},
        "strict_lines_in_middle_third": strict_mid,
        "vague_terms": count_terms(lines, VAGUE),
        "computation_terms": count_terms(lines, COMPUTE),
        "near_duplicate_sentences": dups[:10],
        "tier": a.tier,
        "load_band": {"comfortable_up_to": low, "risky_up_to": high},
        "load_status": "within" if k <= low else ("risky" if k <= high else "over"),
        "all_constraints_pass_probability": {
            f"p={p}": round(p ** max(k, 1), 3) for p in (0.98, 0.95, 0.9)
        },
    }
    if a.corpus:
        out["corpus_overlap"] = corpus_overlap(text, a.corpus)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
