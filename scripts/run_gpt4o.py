"""Run gpt-4o on a measurement split with the same zero-shot prompt and parser as system B.

Reference run, not a shipped system: it shows how far a large hosted model gets
with the identical prompt and scoring. Sends product titles only (no gold) to the
OpenAI API. Needs OPENAI_API_KEY in .env.

  PYTHONPATH=. uv run python scripts/run_gpt4o.py --split dev|test2
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from src.measurement_extraction.config import PREDICTIONS_DIR, SAMPLES_DIR
from src.measurement_extraction.prompts import PROMPT_SHA256, SYSTEM_PROMPT
from src.measurement_extraction.qwen import parse_output

MODEL = "gpt-4o-2024-08-06"
URL = "https://api.openai.com/v1/chat/completions"


def api_key() -> str:
    with open(".env", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return os.environ["OPENAI_API_KEY"]


def call(client: httpx.Client, key: str, title: str) -> tuple[str, dict]:
    body = {
        "model": MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Title: {title}"},
        ],
    }
    for attempt in range(4):
        r = client.post(URL, json=body, headers={"Authorization": f"Bearer {key}"})
        if r.status_code == 200:
            data = r.json()
            return data["choices"][0]["message"]["content"], data["usage"]
        time.sleep(2 * (attempt + 1))
    r.raise_for_status()
    raise RuntimeError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True, choices=["dev", "test2"])
    parser.add_argument(
        "--timing-only",
        type=int,
        default=0,
        help="time N sequential calls, print latency, write nothing",
    )
    args = parser.parse_args()
    with (SAMPLES_DIR / f"{args.split}.csv").open(encoding="utf-8", newline="") as f:
        items = list(csv.DictReader(f))
    key = api_key()
    if args.timing_only:
        import statistics

        with httpx.Client(timeout=60) as client:
            secs = []
            for item in items[: args.timing_only]:
                started = time.perf_counter()
                call(client, key, item["item_name"])
                secs.append(time.perf_counter() - started)
        print(
            f"n={len(secs)} median {statistics.median(secs):.2f}s "
            f"mean {statistics.mean(secs):.2f}s max {max(secs):.2f}s"
        )
        return
    with httpx.Client(timeout=60) as client, ThreadPoolExecutor(8) as pool:
        raws = list(pool.map(lambda i: call(client, key, i["item_name"]), items))
    out = PREDICTIONS_DIR / f"gpt4o_{args.split}.jsonl"
    with out.open("w", encoding="utf-8") as handle:
        for item, (raw, usage) in zip(items, raws, strict=True):
            annotation, status, ungrounded = parse_output(raw, item["item_name"])
            handle.write(
                json.dumps(
                    {
                        "item_code": item["item_code"],
                        "system": "gpt4o",
                        "status": status,
                        "annotation": json.loads(annotation.model_dump_json())
                        if annotation
                        else None,
                        "raw": raw,
                        "ungrounded_source_text": ungrounded,
                        "model": MODEL,
                        "prompt_sha256": PROMPT_SHA256,
                        "tokens": usage,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
