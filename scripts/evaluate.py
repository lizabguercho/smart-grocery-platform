"""Score rules / qwen / cascade against saved human gold for one split.

  PYTHONPATH=. uv run python scripts/evaluate.py --split dev

Only items with state 'saved' are scored, identically for every system. Results
are split by labeling source and by probable title truncation (exactly 24
characters). Dev scores are development numbers, never test results.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.measurement_extraction import gold_log
from src.measurement_extraction.config import (
    GOLD_PATH,
    NORMALIZATION_DIR,
    PREDICTIONS_DIR,
    SAMPLES_DIR,
)
from src.measurement_extraction.evaluation import bootstrap_ci, score_title, summarize
from src.measurement_extraction.schema import Annotation

SYSTEMS = ("rules", "qwen", "cascade")
TRUNCATED_LENGTH = 24


def load_predictions(system: str, split: str) -> dict[str, Annotation | None]:
    path = PREDICTIONS_DIR / f"{system}_{split}.jsonl"
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        out[row["item_code"]] = (
            Annotation.model_validate(row["annotation"]) if row["annotation"] else None
        )
    return out


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.0f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="dev")
    args = parser.parse_args()
    titles = {
        r["item_code"]: r["item_name"]
        for r in csv.DictReader(
            (SAMPLES_DIR / f"{args.split}.csv").open(encoding="utf-8", newline="")
        )
    }
    log = gold_log.read_log(GOLD_PATH)
    latest = gold_log.latest(log)
    first = {}
    for record in log:
        first.setdefault(record["item_code"], record)
    gold = {
        c: Annotation.model_validate(r["annotation"])
        for c, r in latest.items()
        if c in titles and r["state"] == "saved" and r["annotation"]
    }
    pending = [c for c in titles if c not in gold]
    preds = {s: load_predictions(s, args.split) for s in SYSTEMS}

    strata = {
        "all": lambda c: True,
        "labeled from scratch": lambda c: first[c].get("annotator", "human") == "human",
        "confirmed assistant drafts": lambda c: (
            first[c].get("annotator") == "claude-draft"
        ),
        "title exactly 24 chars (probably truncated)": lambda c: (
            len(titles[c].strip()) == TRUNCATED_LENGTH
        ),
        "title not truncated": lambda c: len(titles[c].strip()) != TRUNCATED_LENGTH,
    }
    report: dict = {
        "split": args.split,
        "scored": len(gold),
        "pending_or_unscorable": len(pending),
        "strata": {},
    }
    lines = [
        f"# {args.split.upper()} evaluation (development numbers, not test results)\n",
        f"Scored titles: {len(gold)}; pending/unscorable: {len(pending)}. Same titles for every system.\n",
    ]
    per_title: dict[str, dict[str, bool]] = {s: {} for s in SYSTEMS}
    for name, keep in strata.items():
        codes = [c for c in gold if keep(c)]
        if not codes:
            continue
        report["strata"][name] = {}
        lines += [
            f"\n## {name} (n={len(codes)})\n",
            "| system | presence P / R / F1 | failed | joint entry P / R | exact title | false meas. on none | unit invented | unit F1 | role F1 | scope F1 |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for system in SYSTEMS:
            scores = [
                score_title(titles[c], gold[c], preds[system].get(c)) for c in codes
            ]
            if name == "all":
                per_title[system] = {
                    c: s.exact for c, s in zip(codes, scores, strict=True)
                }
            s = summarize(scores)
            report["strata"][name][system] = s
            exact = [float(x.exact) for x in scores]
            low, high = bootstrap_ci(exact) if len(exact) >= 20 else (None, None)
            ci = f" ({pct(low)}-{pct(high)})" if low is not None else ""
            pr = s["presence"]
            je = s["joint_entries"]
            lines.append(
                f"| {system} | {pct(pr['precision'])} / {pct(pr['recall'])} / {pct(pr['f1'])} "
                f"| {s['presence_failed_predictions']} | {pct(je['precision'])} / {pct(je['recall'])} "
                f"| {s['exact_record']}/{len(codes)}{ci} | {s['false_measurement_on_none']} "
                f"| {s['unsupported_unit_completion']} | {pct(s['unit_macro_f1'])} "
                f"| {pct(s['role_macro_f1'])} | {pct(s['scope_macro_f1'])} |"
            )
    lines.append("\n## Paired exact-title outcomes (all scored titles)\n")
    lines.append(
        "| pair | both correct | first only | second only | both wrong |\n|---|---|---|---|---|"
    )
    for a, b in (("rules", "qwen"), ("rules", "cascade"), ("qwen", "cascade")):
        both = sum(per_title[a][c] and per_title[b][c] for c in gold)
        only_a = sum(per_title[a][c] and not per_title[b][c] for c in gold)
        only_b = sum(per_title[b][c] and not per_title[a][c] for c in gold)
        lines.append(
            f"| {a} vs {b} | {both} | {only_a} | {only_b} | {len(gold) - both - only_a - only_b} |"
        )
    out_dir = NORMALIZATION_DIR / "reports"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{args.split}_eval.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    Path(out_dir / f"{args.split}_eval.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
