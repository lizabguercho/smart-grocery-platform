"""CLI entry for SLM grocery-understanding experiments."""

from __future__ import annotations

import argparse
import logging
import sys

from src.slm_benchmark import BENCHMARK_VERSION
from src.slm_benchmark.dataset import load_benchmark
from src.slm_benchmark.model import (
    DEFAULT_MAX_NEW_TOKENS,
    MODEL_ALIASES,
    build_model,
    resolve_model_id,
)
from src.slm_benchmark.prompt import load_prompt
from src.slm_benchmark.runner import (
    DEFAULT_EXPERIMENTS_ROOT,
    build_config,
    experiment_id_for,
    run_experiment,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a zero-shot SLM grocery-understanding experiment on a "
            "frozen benchmark."
        )
    )
    parser.add_argument(
        "--model",
        required=True,
        help=(
            "Model alias or Hugging Face id. Aliases: "
            + ", ".join(sorted(MODEL_ALIASES))
        ),
    )
    parser.add_argument(
        "--prompt",
        default="zero_shot_v1",
        help="Prompt version stem under src/slm_benchmark/prompts/",
    )
    parser.add_argument(
        "--benchmark",
        default=BENCHMARK_VERSION,
        help="Frozen benchmark id or CSV path",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue an interrupted experiment without overwriting predictions.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=str(DEFAULT_EXPERIMENTS_ROOT),
    )
    parser.add_argument(
        "--experiment-id",
        default=None,
        help="Override default experiment id (<model>_<prompt>).",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=DEFAULT_MAX_NEW_TOKENS,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    rows = load_benchmark(args.benchmark)
    if args.limit is not None:
        rows = rows[: args.limit]

    prompt_config = load_prompt(args.prompt)
    model_id = resolve_model_id(args.model)
    experiment_id = args.experiment_id or experiment_id_for(args.model, args.prompt)
    config = build_config(
        experiment_id=experiment_id,
        benchmark_version=BENCHMARK_VERSION,
        model_alias=args.model,
        model_id=model_id,
        prompt_version=args.prompt,
        max_new_tokens=args.max_new_tokens,
        limit=args.limit,
    )

    logging.info(
        "Experiment %s | model=%s prompt=%s n=%s",
        experiment_id,
        model_id,
        args.prompt,
        len(rows),
    )
    model = build_model(args.model, max_new_tokens=args.max_new_tokens)
    try:
        run_experiment(
            model=model,
            prompt_config=prompt_config,
            rows=rows,
            experiment_id=experiment_id,
            config=config,
            output_root=__import__("pathlib").Path(args.output_root),
            resume=args.resume,
        )
    except FileExistsError as exc:
        logging.error("%s", exc)
        return 1
    except Exception:
        logging.exception("Experiment failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
