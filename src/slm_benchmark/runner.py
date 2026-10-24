"""Run a frozen-benchmark experiment and write predictions + metrics."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.slm_benchmark.dataset import load_benchmark
from src.slm_benchmark.metrics import ScoredPrediction, compute_metrics, failure_rows
from src.slm_benchmark.model import GroceryUnderstandingModel
from src.slm_benchmark.parse import parse_model_output
from src.slm_benchmark.prompt import PromptConfig, load_prompt
from src.slm_benchmark.schema import BenchmarkRow

logger = logging.getLogger(__name__)

DEFAULT_EXPERIMENTS_ROOT = Path("experiments/slm_benchmark")


def experiment_id_for(model_alias: str, prompt_version: str) -> str:
    alias = model_alias.replace("/", "_").replace(":", "_")
    return f"{alias}_{prompt_version}"


def experiment_dir(
    experiment_id: str, root: Path = DEFAULT_EXPERIMENTS_ROOT
) -> Path:
    return root / experiment_id


def build_config(
    *,
    experiment_id: str,
    benchmark_version: str,
    model_alias: str,
    model_id: str,
    prompt_version: str,
    max_new_tokens: int,
    limit: int | None,
) -> dict[str, Any]:
    return {
        "experiment_id": experiment_id,
        "benchmark_version": benchmark_version,
        "model_alias": model_alias,
        "model_id": model_id,
        "prompt_version": prompt_version,
        "temperature": 0,
        "do_sample": False,
        "max_new_tokens": max_new_tokens,
        "dtype": "auto",
        "quantization": None,
        "device": "auto",
        "constrained_decoding": False,
        "limit": limit,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _prediction_payload(
    row: BenchmarkRow,
    *,
    experiment_id: str,
    raw_text: str,
    parse_success: bool,
    prediction: Any,
    latency_seconds: float,
    error_message: str | None,
) -> dict[str, Any]:
    pred_fields = (
        prediction.model_dump()
        if prediction is not None
        else {
            "is_product": None,
            "category": None,
            "brand": None,
            "normalized_name_en": None,
            "quantity": None,
            "unit": None,
        }
    )
    return {
        "experiment_id": experiment_id,
        "item_code": row.item_code,
        "raw_item_name": row.raw_item_name,
        "raw_model_output": raw_text,
        "parse_success": parse_success,
        "error_message": error_message,
        "latency_seconds": latency_seconds,
        "gold_is_product": row.is_product,
        "gold_category": row.category,
        "gold_slice_tags": row.slice_tags,
        "pred_is_product": pred_fields["is_product"],
        "pred_category": pred_fields["category"],
        "pred_brand": pred_fields["brand"],
        "pred_normalized_name_en": pred_fields["normalized_name_en"],
        "pred_quantity": pred_fields["quantity"],
        "pred_unit": pred_fields["unit"],
    }


def _load_completed_codes(predictions_path: Path) -> set[str]:
    if not predictions_path.is_file():
        return set()
    done: set[str] = set()
    with predictions_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            done.add(str(payload["item_code"]))
    return done


def _load_scored_from_predictions(
    predictions_path: Path,
    rows_by_code: dict[str, BenchmarkRow],
) -> list[ScoredPrediction]:
    scored: list[ScoredPrediction] = []
    with predictions_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            row = rows_by_code[str(payload["item_code"])]
            parsed = parse_model_output(payload.get("raw_model_output") or "")
            scored.append(
                ScoredPrediction(
                    row=row,
                    parse_success=bool(payload.get("parse_success")),
                    prediction=parsed.prediction if payload.get("parse_success") else None,
                    latency_seconds=float(payload.get("latency_seconds") or 0.0),
                    error_message=payload.get("error_message"),
                    raw_model_output=payload.get("raw_model_output") or "",
                )
            )
    return scored


def write_metrics_and_errors(
    scored: list[ScoredPrediction],
    out_dir: Path,
) -> dict[str, Any]:
    metrics = compute_metrics(scored)
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    errors = failure_rows(scored)
    error_path = out_dir / "errors.csv"
    fieldnames = [
        "item_code",
        "raw_item_name",
        "gold_is_product",
        "gold_category",
        "pred_is_product",
        "pred_category",
        "failed_fields",
        "parse_success",
        "error_message",
        "raw_model_output",
        "slice_tags",
    ]
    with error_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in errors:
            writer.writerow(row)
    return metrics


def run_experiment(
    *,
    model: GroceryUnderstandingModel,
    prompt_config: PromptConfig,
    rows: list[BenchmarkRow],
    experiment_id: str,
    config: dict[str, Any],
    output_root: Path = DEFAULT_EXPERIMENTS_ROOT,
    resume: bool = False,
) -> dict[str, Any]:
    out_dir = experiment_dir(experiment_id, output_root)
    predictions_path = out_dir / "predictions.jsonl"
    config_path = out_dir / "config.json"

    if out_dir.exists() and not resume:
        if (out_dir / "metrics.json").exists() or predictions_path.exists():
            raise FileExistsError(
                f"Experiment directory already exists: {out_dir}. "
                "Pass --resume to continue, or choose a new experiment id."
            )
    out_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    rows_by_code = {row.item_code: row for row in rows}
    completed = _load_completed_codes(predictions_path) if resume else set()
    if completed:
        logger.info("Resuming; %s prediction(s) already on disk", len(completed))

    mode = "a" if resume and predictions_path.exists() else "w"
    with predictions_path.open(mode, encoding="utf-8") as handle:
        for index, row in enumerate(rows, start=1):
            if row.item_code in completed:
                continue
            logger.info(
                "[%s/%s] item_code=%s name=%r",
                index,
                len(rows),
                row.item_code,
                row.raw_item_name,
            )
            try:
                response = model.generate(row.raw_item_name, prompt_config)
                raw_text = response.raw_text
                latency = response.latency_seconds
                error_message = None
            except Exception as exc:
                logger.exception("Inference failed for item_code=%s", row.item_code)
                raw_text = ""
                latency = 0.0
                error_message = f"inference_error:{type(exc).__name__}"

            if error_message is None:
                parsed = parse_model_output(raw_text)
                parse_success = parsed.parse_success
                prediction = parsed.prediction
                error_message = parsed.error_message
            else:
                parse_success = False
                prediction = None

            payload = _prediction_payload(
                row,
                experiment_id=experiment_id,
                raw_text=raw_text,
                parse_success=parse_success,
                prediction=prediction,
                latency_seconds=latency,
                error_message=error_message,
            )
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            handle.flush()

    scored = _load_scored_from_predictions(predictions_path, rows_by_code)
    metrics = write_metrics_and_errors(scored, out_dir)
    readme = out_dir / "README.md"
    readme.write_text(
        "\n".join(
            [
                f"# Experiment `{experiment_id}`",
                "",
                f"- model: `{config['model_id']}`",
                f"- prompt: `{config['prompt_version']}`",
                f"- benchmark: `{config['benchmark_version']}`",
                f"- n predictions: {metrics['n']}",
                f"- parse success: {metrics['structural']['parse_success_rate']:.3f}",
                f"- category macro-F1: {metrics['category']['macro_f1']:.3f}",
                "",
                "Files: `config.json`, `predictions.jsonl`, `metrics.json`, `errors.csv`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    logger.info(
        "Done. parse_success=%.3f category_macro_f1=%.3f is_product_f1=%.3f",
        metrics["structural"]["parse_success_rate"],
        metrics["category"]["macro_f1"],
        metrics["is_product"]["f1"],
    )
    return metrics
