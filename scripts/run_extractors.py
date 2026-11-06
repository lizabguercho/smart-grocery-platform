"""Run extraction systems over a sample split and write predictions as JSONL.

  PYTHONPATH=. uv run --group transformers python scripts/run_extractors.py \
      --system rules|qwen|cascade --split dev|test [--limit N]

Predictions go to research/normalization/predictions/ and are never shown by
the annotation page. Qwen is resumable: titles already in the file are skipped.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import time
from pathlib import Path

from src.measurement_extraction import cascade, rules
from src.measurement_extraction.config import PREDICTIONS_DIR, SAMPLES_DIR
from src.measurement_extraction.prompts import PROMPT_SHA256


def load(split: str) -> list[dict]:
    with (SAMPLES_DIR / f"{split}.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def dump(annotation) -> dict | None:
    return json.loads(annotation.model_dump_json()) if annotation else None


def run_rules(items, out: Path) -> None:
    with out.open("w", encoding="utf-8") as handle:
        for item in items:
            result = rules.extract(item["item_name"])
            handle.write(
                json.dumps(
                    {
                        "item_code": item["item_code"],
                        "system": "rules",
                        "status": "ok",
                        "annotation": dump(result.annotation),
                        "rule_ids": result.rule_ids,
                        "spans": result.spans,
                        "eligible": result.eligible,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def run_qwen(items, out: Path, batch_size: int, backend: str) -> None:
    from src.measurement_extraction.qwen import (
        MLX_DESCRIPTION,
        MODEL_ID,
        MODEL_REVISION,
        BatchWorker,
        MlxQwenExtractor,
        QwenExtractor,
    )

    done = {r["item_code"] for r in read(out)}
    todo = [i for i in items if i["item_code"] not in done]
    if not todo:
        return
    started = time.perf_counter()
    extractor = MlxQwenExtractor() if backend == "mlx" else QwenExtractor()
    load_seconds = time.perf_counter() - started
    print(
        f"model loaded in {load_seconds:.0f}s on {extractor.device}, batch {batch_size}",
        flush=True,
    )

    async def go() -> None:
        finished = 0
        with out.open("a", encoding="utf-8") as handle:
            async with BatchWorker(extractor, batch_size) as worker:

                async def one(item: dict) -> None:
                    nonlocal finished
                    result = await worker.submit(item["item_name"])
                    handle.write(
                        json.dumps(
                            {
                                "item_code": item["item_code"],
                                "system": "qwen",
                                "status": result.status,
                                "annotation": dump(result.annotation),
                                "raw": result.raw,
                                "ungrounded_source_text": result.ungrounded,
                                "seconds": round(result.seconds, 2),
                                "batch_size": result.batch_size,
                                "new_tokens": result.new_tokens,
                                "backend": backend,
                                "model": MLX_DESCRIPTION
                                if backend == "mlx"
                                else MODEL_ID,
                                "revision": MODEL_REVISION,
                                "prompt_sha256": PROMPT_SHA256,
                                "device": extractor.device,
                                "decoding": "greedy, enable_thinking=False, max_new_tokens=256, 1 attempt",
                                "model_load_seconds": round(load_seconds, 1),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    handle.flush()
                    finished += 1
                    print(
                        f"{finished}/{len(todo)} {result.status} batch={result.batch_size}",
                        flush=True,
                    )

                await asyncio.gather(*(one(item) for item in todo))

    asyncio.run(go())


def run_cascade(items, split: str, out: Path) -> None:
    rule_rows = {
        r["item_code"]: r for r in read(PREDICTIONS_DIR / f"rules_{split}.jsonl")
    }
    qwen_rows = {
        r["item_code"]: r for r in read(PREDICTIONS_DIR / f"qwen_{split}.jsonl")
    }
    with out.open("w", encoding="utf-8") as handle:
        for item in items:
            code = item["item_code"]
            rule_result = rules.extract(item["item_name"])
            chosen = cascade.route(rule_result)
            source = rule_rows[code] if chosen == "rules" else qwen_rows.get(code)
            if source is None:
                row = {
                    "item_code": code,
                    "system": "cascade",
                    "status": "pending_qwen",
                    "routed_to": chosen,
                    "annotation": None,
                }
            else:
                row = {
                    **source,
                    "system": "cascade",
                    "routed_to": chosen,
                    "qwen_reused_from_cache": chosen == "qwen",
                }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["rules", "qwen", "cascade"], required=True)
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--backend", choices=["mlx", "torch"], default="mlx")
    args = parser.parse_args()
    items = load(args.split)[: args.limit]
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out = PREDICTIONS_DIR / f"{args.system}_{args.split}.jsonl"
    {
        "rules": lambda: run_rules(items, out),
        "qwen": lambda: run_qwen(items, out, args.batch_size, args.backend),
        "cascade": lambda: run_cascade(items, args.split, out),
    }[args.system]()
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
