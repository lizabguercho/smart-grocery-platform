"""Scoring: one-to-one measurement matching and field/record metrics.

Gold and predictions are compared only after the shared canonicalization.
A failed prediction (no parsed annotation) is a system failure, never "none".
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal

from src.measurement_extraction.schema import Annotation, Measurement
from src.measurement_extraction.units import apply_canonical

# Singular/abbreviation equivalences built from the dev annotations.
COUNTED_ITEM_MAP = {
    "שקיקים": "שקיק",
    "שקיות": "שקית",
    "מברשות": "מברשת",
    "כמוסות": "כמוסה",
    "כמ": "כמוסה",
    "יח": "יחידה",
    "יחי": "יחידה",
    "יחידות": "יחידה",
}
FIELDS = ("unit", "amount", "family", "role", "scope", "package_count", "counted_item")


def _num(value: Decimal | None) -> Decimal | None:
    return None if value is None else value.normalize()


@dataclass(frozen=True)
class Canon:
    """Canonical comparable view of one measurement entry."""

    unit: str | None
    amount: (
        Decimal | None
    )  # canonical amount, or the raw number when the unit is unresolved
    family: str | None
    role: str | None
    scope: str | None
    package_count: int | None
    counted_item: str | None
    span: tuple[int, int] | None
    raw_amount: Decimal | None


def canon(entry: Measurement, title: str) -> Canon:
    entry = apply_canonical(entry)
    item = (entry.counted_item or "").strip() or None
    item = COUNTED_ITEM_MAP.get(item, item)
    family = entry.describes.value if entry.describes else None
    at = title.find(entry.source_text) if entry.source_text else -1
    return Canon(
        unit=entry.unit,
        amount=_num(entry.amount if entry.unit else entry.source_amount),
        family=family,
        role=entry.measurement_role.value if entry.measurement_role else None,
        scope=entry.amount_scope.value if entry.amount_scope else None,
        package_count=entry.package_count,
        counted_item=item,
        span=(at, at + len(entry.source_text)) if at >= 0 else None,
        raw_amount=_num(entry.source_amount),
    )


def _link(g: Canon, p: Canon) -> int:
    if g.span and p.span and g.span[0] < p.span[1] and p.span[0] < g.span[1]:
        return 3
    if g.raw_amount is not None and g.raw_amount == p.raw_amount:
        return 2
    if g.package_count is not None and g.package_count == p.package_count:
        return 1
    return 0


def match(gold: list[Canon], pred: list[Canon]) -> list[tuple[int, int]]:
    """Deterministic one-to-one matching: strongest link first, ties by position."""

    links = sorted(
        (
            (-_link(g, p), i, j)
            for i, g in enumerate(gold)
            for j, p in enumerate(pred)
            if _link(g, p)
        ),
    )
    used_g, used_p, pairs = set(), set(), []
    for _, i, j in links:
        if i not in used_g and j not in used_p:
            used_g.add(i)
            used_p.add(j)
            pairs.append((i, j))
    return sorted(pairs)


@dataclass
class TitleScore:
    gold_has: bool
    pred_has: bool
    failed: bool
    n_gold: int
    n_pred: int
    pairs: list[dict]  # per matched pair: field -> bool, plus "joint"
    unsupported_unit: int  # predicted a unit where gold has none
    exact: bool


def score_title(title: str, gold: Annotation, pred: Annotation | None) -> TitleScore:
    g = [canon(m, title) for m in gold.measurements]
    if pred is None:
        return TitleScore(gold.has_measurement, False, True, len(g), 0, [], 0, False)
    p = [canon(m, title) for m in pred.measurements]
    pairs, unsupported = [], 0
    for i, j in match(g, p):
        row = {f: getattr(g[i], f) == getattr(p[j], f) for f in FIELDS}
        row["joint"] = all(row.values())
        row["gold"] = {f: getattr(g[i], f) for f in ("unit", "family", "role", "scope")}
        row["pred"] = {f: getattr(p[j], f) for f in ("unit", "family", "role", "scope")}
        unsupported += g[i].unit is None and p[j].unit is not None
        pairs.append(row)
    joint = sum(r["joint"] for r in pairs)
    exact = joint == len(g) == len(p) and gold.has_measurement == pred.has_measurement
    return TitleScore(
        gold.has_measurement,
        pred.has_measurement,
        False,
        len(g),
        len(p),
        pairs,
        unsupported,
        exact,
    )


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = (
        2 * p * r / (p + r)
        if p and r
        else (0.0 if p is not None and r is not None else None)
    )
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f}


def macro_f1(pairs: list[tuple]) -> dict:
    """Macro-F1 over (gold_label, pred_label) pairs; None is the label 'null'."""

    labels = {a for a, _ in pairs} | {b for _, b in pairs}
    per = {}
    for label in labels:
        tp = sum(a == label and b == label for a, b in pairs)
        fp = sum(a != label and b == label for a, b in pairs)
        fn = sum(a == label and b != label for a, b in pairs)
        per[str(label)] = {**prf(tp, fp, fn), "support": tp + fn}
    scored = [v["f1"] for v in per.values() if v["f1"] is not None]
    return {"macro_f1": sum(scored) / len(scored) if scored else None, "per_label": per}


def summarize(scores: list[TitleScore]) -> dict:
    n = len(scores)
    tp = sum(s.gold_has and s.pred_has for s in scores)
    fp = sum(not s.gold_has and s.pred_has for s in scores)
    fn = sum(s.gold_has and not s.pred_has for s in scores)  # failures count as missed
    pairs = [r for s in scores for r in s.pairs]
    matched = len(pairs)
    n_gold = sum(s.n_gold for s in scores)
    n_pred = sum(s.n_pred for s in scores)
    joint = sum(r["joint"] for r in pairs)
    out = {
        "titles": n,
        "presence": prf(tp, fp, fn),
        "presence_failed_predictions": sum(s.failed for s in scores),
        "gold_entries": n_gold,
        "pred_entries": n_pred,
        "matched_entries": matched,
        "field_accuracy_on_matched": {
            f: (sum(r[f] for r in pairs) / matched if matched else None) for f in FIELDS
        },
        "joint_entries": prf(joint, n_pred - joint, n_gold - joint),
        "exact_record": sum(s.exact for s in scores),
        "false_measurement_on_none": fp,
        "unsupported_unit_completion": sum(s.unsupported_unit for s in scores),
    }
    for f in ("unit", "family", "role", "scope"):
        out[f"{f}_macro_f1"] = macro_f1([(r["gold"][f], r["pred"][f]) for r in pairs])[
            "macro_f1"
        ]
    return out


def bootstrap_ci(
    values: list[float], samples: int = 2000, seed: int = 20261027
) -> tuple[float, float]:
    """95% percentile interval of the mean, resampling titles."""

    rng = random.Random(seed)
    means = sorted(
        sum(rng.choices(values, k=len(values))) / len(values) for _ in range(samples)
    )
    return means[int(0.025 * samples)], means[int(0.975 * samples) - 1]
