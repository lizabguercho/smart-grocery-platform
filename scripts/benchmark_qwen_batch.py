"""Time Qwen at several batch sizes on titles already run at batch 1.

Prints seconds per title, peak MLX memory, and how many outputs differ from
the bf16 partial run (the 4-bit model may legitimately differ).
"""

from __future__ import annotations

import json
import sys
import time

import mlx.core as mx

from scripts.run_extractors import load, read
from src.measurement_extraction.config import PREDICTIONS_DIR
from src.measurement_extraction.qwen import MlxQwenExtractor

SIZES = [int(x) for x in sys.argv[1:]] or [4, 8, 12, 16]
N_TITLES = max(SIZES)


def main() -> None:
    reference = {
        r["item_code"]: r for r in read(PREDICTIONS_DIR / "qwen_bf16_dev_partial.jsonl")
    }
    items = [i for i in load("dev") if i["item_code"] in reference][:N_TITLES]
    print(
        f"{len(items)} titles; batch-1 reference mean "
        f"{sum(reference[i['item_code']]['seconds'] for i in items) / len(items):.1f}s/title",
        flush=True,
    )
    extractor = MlxQwenExtractor()
    extractor.extract_batch([items[0]["item_name"]])  # warm-up
    for size in SIZES:
        started = time.perf_counter()
        outputs = []
        for at in range(0, len(items), size):
            outputs += extractor.extract_batch(
                [i["item_name"] for i in items[at : at + size]]
            )
        total = time.perf_counter() - started
        differ = sum(
            o.raw.strip() != reference[i["item_code"]]["raw"].strip()
            for o, i in zip(outputs, items)
        )
        bad = sum(o.status != "ok" for o in outputs)
        peak = mx.get_peak_memory() / 1e9
        print(
            json.dumps(
                {
                    "batch": size,
                    "sec_per_title": round(total / len(items), 2),
                    "total_s": round(total, 1),
                    "mlx_peak_gb": round(peak, 1),
                    "differs_from_batch1": differ,
                    "non_ok": bad,
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
