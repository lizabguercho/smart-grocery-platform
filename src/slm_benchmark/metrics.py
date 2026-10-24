"""Deterministic Tier-1 evaluation for the grocery-understanding benchmark."""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass
from typing import Any

from src.slm_benchmark.categories import ALLOWED_CATEGORIES
from src.slm_benchmark.schema import BenchmarkRow, GroceryUnderstandingPrediction


@dataclass(frozen=True)
class ScoredPrediction:
    row: BenchmarkRow
    parse_success: bool
    prediction: GroceryUnderstandingPrediction | None
    latency_seconds: float
    error_message: str | None = None
    raw_model_output: str = ""


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _binary_prf(
    y_true: list[bool], y_pred: list[bool]
) -> dict[str, float]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(tp + tn, len(y_true)) if y_true else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "tn": float(tn),
    }


def _category_metrics(
    gold_categories: list[str],
    pred_categories: list[str | None],
) -> dict[str, Any]:
    labels = list(ALLOWED_CATEGORIES)
    confusion: dict[str, dict[str, int]] = {
        label: {other: 0 for other in labels + ["__invalid_or_missing__"]}
        for label in labels
    }
    correct = 0
    per_class: dict[str, dict[str, float]] = {}

    for gold, pred in zip(gold_categories, pred_categories):
        bucket = pred if pred in labels else "__invalid_or_missing__"
        confusion[gold][bucket] += 1
        if pred == gold:
            correct += 1

    f1_scores: list[float] = []
    for label in labels:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in labels if other != label)
        fn = sum(
            count
            for other, count in confusion[label].items()
            if other != label
        )
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        support = sum(confusion[label].values())
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": float(support),
        }
        if support > 0:
            f1_scores.append(f1)

    return {
        "n": len(gold_categories),
        "accuracy": _safe_div(correct, len(gold_categories)),
        "macro_f1": statistics.mean(f1_scores) if f1_scores else 0.0,
        "per_class": per_class,
        "confusion": confusion,
    }


def compute_metrics(scored: list[ScoredPrediction]) -> dict[str, Any]:
    n = len(scored)
    parse_ok = sum(1 for item in scored if item.parse_success)

    is_true = [item.row.is_product for item in scored]
    is_pred: list[bool] = []
    for item in scored:
        if item.parse_success and item.prediction is not None:
            is_pred.append(item.prediction.is_product)
        else:
            # Unparsed rows count as incorrect is_product predictions.
            is_pred.append(not item.row.is_product)

    category_gold: list[str] = []
    category_pred: list[str | None] = []
    valid_category_among_product_preds = 0
    product_preds = 0

    for item in scored:
        if not item.row.is_product or item.row.category is None:
            continue
        category_gold.append(item.row.category)
        if item.parse_success and item.prediction is not None:
            pred_cat = item.prediction.category
            category_pred.append(pred_cat)
            if item.prediction.is_product:
                product_preds += 1
                if pred_cat in ALLOWED_CATEGORIES:
                    valid_category_among_product_preds += 1
        else:
            category_pred.append(None)

    latencies = [item.latency_seconds for item in scored]
    latencies_sorted = sorted(latencies)
    p95 = (
        latencies_sorted[max(0, math.ceil(0.95 * len(latencies_sorted)) - 1)]
        if latencies_sorted
        else 0.0
    )
    total_runtime = sum(latencies)

    return {
        "n": n,
        "structural": {
            "parse_success_rate": _safe_div(parse_ok, n),
            "parse_success_count": parse_ok,
            "valid_category_rate_among_product_preds": _safe_div(
                valid_category_among_product_preds, product_preds
            ),
        },
        "is_product": _binary_prf(is_true, is_pred),
        "category": _category_metrics(category_gold, category_pred),
        "efficiency": {
            "total_runtime_seconds": total_runtime,
            "mean_latency_seconds": statistics.mean(latencies) if latencies else 0.0,
            "median_latency_seconds": (
                statistics.median(latencies) if latencies else 0.0
            ),
            "p95_latency_seconds": p95,
            "items_per_second": _safe_div(n, total_runtime),
        },
    }


def failure_rows(scored: list[ScoredPrediction]) -> list[dict[str, Any]]:
    """Rows suitable for errors.csv (parse fails + Tier-1 mistakes)."""

    rows: list[dict[str, Any]] = []
    for item in scored:
        failed_fields: list[str] = []
        pred = item.prediction
        if not item.parse_success:
            failed_fields.append("parse")
        else:
            assert pred is not None
            if pred.is_product != item.row.is_product:
                failed_fields.append("is_product")
            if item.row.is_product and item.row.category is not None:
                if pred.category != item.row.category:
                    failed_fields.append("category")

        if not failed_fields:
            continue

        rows.append(
            {
                "item_code": item.row.item_code,
                "raw_item_name": item.row.raw_item_name,
                "gold_is_product": item.row.is_product,
                "gold_category": item.row.category or "",
                "pred_is_product": (
                    "" if pred is None else pred.is_product
                ),
                "pred_category": "" if pred is None else (pred.category or ""),
                "failed_fields": ";".join(failed_fields),
                "parse_success": item.parse_success,
                "error_message": item.error_message or "",
                "raw_model_output": item.raw_model_output,
                "slice_tags": item.row.slice_tags,
            }
        )

    rows.sort(key=lambda row: (row["failed_fields"], row["item_code"]))
    return rows


def slice_counts(rows: list[BenchmarkRow]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        for tag in row.tags:
            counter[tag] += 1
    return dict(sorted(counter.items()))


def category_histogram(rows: list[BenchmarkRow]) -> dict[str, int]:
    counter: Counter[str] = Counter(
        row.category or "__null__" for row in rows if row.is_product
    )
    return dict(sorted(counter.items()))
