"""Generate candidate English / SKU annotations with a cloud LLM (not Qwen).

Candidates are NEVER copied into gold fields. Human review is required.

Usage:
  PYTHONPATH=. uv run python -m src.slm_benchmark.annotate_candidates
  PYTHONPATH=. uv run python -m src.slm_benchmark.annotate_candidates --limit 5
  PYTHONPATH=. uv run python -m src.slm_benchmark.annotate_candidates --resume
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.slm_benchmark.annotation_io import (
    V2_ANNOTATIONS_CSV,
    load_annotations,
    rows_from_v1,
    write_annotations,
)
from src.slm_benchmark.annotation_schema import (
    AnnotationStatus,
    CandidateSkuFields,
)
from src.slm_benchmark.dataset import DEFAULT_BENCHMARK_CSV, load_benchmark
from src.slm_benchmark.prompt import PROMPTS_DIR

logger = logging.getLogger(__name__)

DEFAULT_ANNOTATOR_MODEL = os.getenv("AGENT_MODEL", "openai-chat:gpt-4o-mini")


def _load_system_prompt() -> str:
    path = PROMPTS_DIR / "annotation_assistant_v1.txt"
    return path.read_text(encoding="utf-8").strip()


def _build_user_prompt(
    *,
    raw_item_name: str,
    is_product: bool,
    manufacture_name: str | None,
) -> str:
    lines = [
        f"raw_item_name: {raw_item_name}",
        f"is_product: {is_product}",
    ]
    if manufacture_name:
        lines.append(
            f"manufacture_name_hint: {manufacture_name} "
            "(hint only — prefer evidence in the product name)"
        )
    return "\n".join(lines)


def annotate_one(
    *,
    raw_item_name: str,
    is_product: bool,
    manufacture_name: str | None,
    model_id: str,
) -> CandidateSkuFields:
    """Call the cloud annotation assistant for one row."""

    if not is_product:
        return CandidateSkuFields()

    from pydantic_ai import Agent

    agent: Agent[None, CandidateSkuFields] = Agent(
        model_id,
        output_type=CandidateSkuFields,
        instructions=_load_system_prompt(),
    )
    user_prompt = _build_user_prompt(
        raw_item_name=raw_item_name,
        is_product=is_product,
        manufacture_name=manufacture_name,
    )
    result = agent.run_sync(user_prompt)
    return result.output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate v2 candidate annotations (not gold)."
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=DEFAULT_BENCHMARK_CSV,
        help="Frozen v1 CSV (source of item_codes / Hebrew names).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=V2_ANNOTATIONS_CSV,
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_ANNOTATOR_MODEL,
        help="pydantic-ai model string (must not be the Qwen SLM under test).",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip rows that already have candidate_name_en or non-product candidates filled.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing annotations file from scratch (ignored with --resume).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if "qwen" in args.model.casefold():
        logger.error(
            "Refusing model %r — annotation assistant must not be the Qwen "
            "family under evaluation.",
            args.model,
        )
        return 1

    v1 = load_benchmark(args.benchmark)
    if args.output.exists() and args.resume:
        rows = load_annotations(args.output)
        by_code = {row.item_code: row for row in rows}
        # Ensure all v1 codes present.
        for seed in rows_from_v1(v1):
            by_code.setdefault(seed.item_code, seed)
        rows = [by_code[row.item_code] for row in v1]
    elif args.output.exists() and not args.force and not args.resume:
        logger.error(
            "%s exists. Pass --resume to continue or --force to rebuild.",
            args.output,
        )
        return 1
    else:
        rows = rows_from_v1(v1)

    if args.limit is not None:
        target_codes = {row.item_code for row in v1[: args.limit]}
    else:
        target_codes = {row.item_code for row in v1}

    done = 0
    for index, row in enumerate(rows, start=1):
        if row.item_code not in target_codes:
            continue
        if args.resume:
            already_has_candidates = bool(row.annotator_model_id) and (
                row.candidate_name_en is not None or not row.is_product
            )
            # Human may have labeled before candidates existed; never overwrite.
            already_reviewed = row.annotation_status != AnnotationStatus.UNREVIEWED
            if already_has_candidates or already_reviewed:
                continue

        logger.info(
            "[%s] item_code=%s is_product=%s name=%r",
            index,
            row.item_code,
            row.is_product,
            row.raw_item_name,
        )
        try:
            fields = annotate_one(
                raw_item_name=row.raw_item_name,
                is_product=row.is_product,
                manufacture_name=row.manufacture_name,
                model_id=args.model,
            )
        except Exception:
            logger.exception("Annotation failed for item_code=%s", row.item_code)
            write_annotations(rows, args.output)
            return 1

        status_before = row.annotation_status
        gold_before = row.gold_name_en
        row.apply_candidates(fields, args.model)
        # Candidates only — never mutate gold / review status.
        assert row.annotation_status == status_before
        assert row.gold_name_en == gold_before
        done += 1
        if done % 5 == 0:
            write_annotations(rows, args.output)

    write_annotations(rows, args.output)
    logger.info(
        "Wrote %s annotation row(s) to %s (updated %s this run)",
        len(rows),
        args.output,
        done,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
