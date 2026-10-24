"""Layer 1–2 re-evaluation of saved SLM predictions against v2 gold.

Does NOT reload models. Writes a new experiment directory
`<source_experiment_id>__eval_v2/` without overwriting v1 metrics.

Usage:
  PYTHONPATH=. uv run python -m src.slm_benchmark.eval_translation \\
    --predictions experiments/slm_benchmark/qwen25_15b_zero_shot_v1/predictions.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any

from src.slm_benchmark.annotation_io import V2_GOLD_CSV, load_gold
from src.slm_benchmark.annotation_schema import AnnotationRow
from src.slm_benchmark.normalize import (
    null_aware_str_match,
    quantities_match,
    units_match,
)
from src.slm_benchmark.runner import DEFAULT_EXPERIMENTS_ROOT

logger = logging.getLogger(__name__)

ATTRIBUTE_FIELDS = (
    "brand",
    "product_type",
    "variant",
    "quantity",
    "unit",
    "pack_count",
    "percent",
)


def load_predictions(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _field_match(
    field: str, gold: AnnotationRow, pred: dict[str, Any]
) -> bool | None:
    """Return True/False, or None when the field cannot be scored from old preds."""

    if field == "brand":
        return null_aware_str_match(gold.gold_brand, pred.get("pred_brand"))
    if field == "product_type":
        # Old prompt had no product_type field — unscored.
        return None
    if field == "variant":
        return None
    if field == "quantity":
        return quantities_match(gold.gold_quantity, pred.get("pred_quantity"))
    if field == "unit":
        return units_match(gold.gold_unit, pred.get("pred_unit"))
    if field == "pack_count":
        return None
    if field == "percent":
        return None
    raise KeyError(field)


def _critical_miss(gold: AnnotationRow, pred: dict[str, Any]) -> bool:
    """Wrong/missing product identity signals available from saved preds."""

    if not gold.is_product:
        return False
    # Empty English when gold has a name is a critical miss for translation.
    gold_name = (gold.gold_name_en or "").strip()
    pred_name = (pred.get("pred_normalized_name_en") or "").strip()
    if gold_name and not pred_name:
        return True
    if gold.gold_brand and not null_aware_str_match(
        gold.gold_brand, pred.get("pred_brand")
    ):
        # Brand only scored when gold specifies one; mismatch = critical.
        return True
    if gold.gold_quantity is not None and not quantities_match(
        gold.gold_quantity, pred.get("pred_quantity")
    ):
        return True
    if gold.gold_unit is not None and not units_match(
        gold.gold_unit, pred.get("pred_unit")
    ):
        return True
    return False


def evaluate(
    gold_rows: list[AnnotationRow],
    predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    gold_by_code = {row.item_code: row for row in gold_rows}
    joined: list[tuple[AnnotationRow, dict[str, Any]]] = []
    missing_gold = 0
    for pred in predictions:
        code = str(pred["item_code"])
        gold = gold_by_code.get(code)
        if gold is None:
            missing_gold += 1
            continue
        joined.append((gold, pred))

    product_pairs = [(g, p) for g, p in joined if g.is_product]
    non_product_pairs = [(g, p) for g, p in joined if not g.is_product]

    # Layer 1: is_product / category (same as v1 methodology on joined set)
    is_true = [g.is_product for g, _ in joined]
    is_pred = []
    for _, pred in joined:
        value = pred.get("pred_is_product")
        if value is None:
            is_pred.append(False)
        else:
            is_pred.append(bool(value))

    def binary_f1(y_true: list[bool], y_hat: list[bool]) -> dict[str, float]:
        tp = sum(1 for t, p in zip(y_true, y_hat) if t and p)
        fp = sum(1 for t, p in zip(y_true, y_hat) if not t and p)
        fn = sum(1 for t, p in zip(y_true, y_hat) if t and not p)
        tn = sum(1 for t, p in zip(y_true, y_hat) if not t and not p)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        accuracy = (tp + tn) / len(y_true) if y_true else 0.0
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    category_correct = 0
    category_n = 0
    for gold, pred in product_pairs:
        if gold.category is None:
            continue
        category_n += 1
        if pred.get("pred_category") == gold.category:
            category_correct += 1

    # Layer 1 structured qty/unit on products
    qty_correct = unit_correct = qty_n = unit_n = 0
    for gold, pred in product_pairs:
        if gold.gold_quantity is not None:
            qty_n += 1
            if quantities_match(gold.gold_quantity, pred.get("pred_quantity")):
                qty_correct += 1
        if gold.gold_unit is not None:
            unit_n += 1
            if units_match(gold.gold_unit, pred.get("pred_unit")):
                unit_correct += 1

    # Layer 2 attribute checklist
    attr_scores: dict[str, dict[str, float]] = {}
    for field in ATTRIBUTE_FIELDS:
        scored = 0
        correct = 0
        for gold, pred in product_pairs:
            result = _field_match(field, gold, pred)
            if result is None:
                continue
            scored += 1
            if result:
                correct += 1
        attr_scores[field] = {
            "n": float(scored),
            "accuracy": (correct / scored) if scored else 0.0,
            "note": (
                "unscored_from_v1_predictions"
                if scored == 0 and field in {"product_type", "variant", "pack_count", "percent"}
                else ""
            ),
        }

    critical_misses = sum(1 for g, p in product_pairs if _critical_miss(g, p))
    name_present = sum(
        1
        for g, p in product_pairs
        if (g.gold_name_en or "").strip()
        and (p.get("pred_normalized_name_en") or "").strip()
    )
    name_missing = sum(
        1
        for g, p in product_pairs
        if (g.gold_name_en or "").strip()
        and not (p.get("pred_normalized_name_en") or "").strip()
    )

    return {
        "evaluation_version": "v2_layers_1_2",
        "n_predictions": len(predictions),
        "n_joined": len(joined),
        "n_missing_gold": missing_gold,
        "n_products": len(product_pairs),
        "n_non_products": len(non_product_pairs),
        "layer1": {
            "is_product": binary_f1(is_true, is_pred),
            "category_accuracy_silver": (
                category_correct / category_n if category_n else 0.0
            ),
            "category_n": category_n,
            "quantity_accuracy": qty_correct / qty_n if qty_n else 0.0,
            "quantity_n": qty_n,
            "unit_accuracy": unit_correct / unit_n if unit_n else 0.0,
            "unit_n": unit_n,
        },
        "layer2": {
            "attribute_accuracy": attr_scores,
            "critical_miss_rate": (
                critical_misses / len(product_pairs) if product_pairs else 0.0
            ),
            "critical_miss_count": critical_misses,
            "pred_name_en_present": name_present,
            "pred_name_en_missing_when_gold": name_missing,
            "note": (
                "product_type/variant/pack/percent not in v1 model schema; "
                "left unscored. English string quality needs Layer 3 judge "
                "or human review of errors."
            ),
        },
    }


def write_translation_errors(
    gold_rows: list[AnnotationRow],
    predictions: list[dict[str, Any]],
    path: Path,
) -> int:
    gold_by_code = {row.item_code: row for row in gold_rows}
    fieldnames = [
        "item_code",
        "raw_item_name",
        "gold_name_en",
        "pred_normalized_name_en",
        "gold_brand",
        "pred_brand",
        "gold_quantity",
        "pred_quantity",
        "gold_unit",
        "pred_unit",
        "critical_miss",
        "failed_fields",
    ]
    n = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for pred in predictions:
            gold = gold_by_code.get(str(pred["item_code"]))
            if gold is None or not gold.is_product:
                continue
            failed: list[str] = []
            for field in ("brand", "quantity", "unit"):
                result = _field_match(field, gold, pred)
                if result is False:
                    failed.append(field)
            if (gold.gold_name_en or "").strip() and not (
                pred.get("pred_normalized_name_en") or ""
            ).strip():
                failed.append("name_en_missing")
            critical = _critical_miss(gold, pred)
            if not failed and not critical:
                continue
            n += 1
            writer.writerow(
                {
                    "item_code": gold.item_code,
                    "raw_item_name": gold.raw_item_name,
                    "gold_name_en": gold.gold_name_en or "",
                    "pred_normalized_name_en": pred.get("pred_normalized_name_en")
                    or "",
                    "gold_brand": gold.gold_brand or "",
                    "pred_brand": pred.get("pred_brand") or "",
                    "gold_quantity": gold.gold_quantity
                    if gold.gold_quantity is not None
                    else "",
                    "pred_quantity": pred.get("pred_quantity")
                    if pred.get("pred_quantity") is not None
                    else "",
                    "gold_unit": gold.gold_unit or "",
                    "pred_unit": pred.get("pred_unit") or "",
                    "critical_miss": critical,
                    "failed_fields": ";".join(failed),
                }
            )
    return n


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-evaluate saved predictions against v2 gold (no inference)."
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        required=True,
        help="Path to an existing predictions.jsonl",
    )
    parser.add_argument("--gold", type=Path, default=V2_GOLD_CSV)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_EXPERIMENTS_ROOT,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing __eval_v2 directory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    predictions = load_predictions(args.predictions)
    if not predictions:
        logger.error("No predictions in %s", args.predictions)
        return 1

    experiment_id = str(predictions[0].get("experiment_id") or args.predictions.parent.name)
    out_dir = args.output_root / f"{experiment_id}__eval_v2"
    if out_dir.exists() and not args.force:
        logger.error("%s exists. Pass --force to overwrite.", out_dir)
        return 1

    try:
        gold_rows = load_gold(args.gold)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    metrics = evaluate(gold_rows, predictions)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics_v2.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    config = {
        "evaluation_version": "v2_layers_1_2",
        "source_predictions": str(args.predictions),
        "source_experiment_id": experiment_id,
        "gold_path": str(args.gold),
        "note": "Re-evaluation only; model outputs were not regenerated.",
    }
    (out_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    n_err = write_translation_errors(
        gold_rows, predictions, out_dir / "translation_errors.csv"
    )
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                f"# Re-evaluation `{out_dir.name}`",
                "",
                f"- source predictions: `{args.predictions}`",
                f"- gold: `{args.gold}`",
                f"- joined: {metrics['n_joined']}",
                f"- critical miss rate: {metrics['layer2']['critical_miss_rate']:.3f}",
                f"- translation error rows: {n_err}",
                "",
                "v1 metrics.json was not modified.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    logger.info(
        "Wrote %s (joined=%s critical_miss_rate=%.3f)",
        out_dir,
        metrics["n_joined"],
        metrics["layer2"]["critical_miss_rate"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
