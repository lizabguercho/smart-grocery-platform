"""Draw the fresh 200-product measurement sample (100 development, 100 test).

Uses the existing Hebrew sampler (random over grocery.products, read-only on
REMOTE_DB_*), with a fixed seed, excluding every product already inspected
(research/samples_product.txt). Oversamples, drops duplicate/near-duplicate
titles, then keeps 200 and splits them 100/100 in drawn (random) order.

  PYTHONPATH=. uv run python scripts/draw_measurement_sample.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import UTC, datetime

from src.database_loader.connection import get_remote_connection
from src.measurement_extraction.config import (
    DEV_SIZE,
    SAMPLE_FILE,
    SAMPLES_DIR,
    SPLIT_SEED,
    TEST_SIZE,
)
from src.measurement_extraction.loader import SampleProduct, load_sample_file
from src.measurement_extraction.manifests import GROUPING_POLICY, group_products
from src.product_translation.sampling import sample_hebrew_products

OVERSAMPLE = 1.3
SETSEED_VALUE = 0.2026  # Postgres setseed() takes [-1, 1]; derived from SPLIT_SEED


def write(path, products) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item_code", "item_name"])
        writer.writerows((p.item_code, p.item_name) for p in products)


def main() -> int:
    if (SAMPLES_DIR / "sample_meta.json").exists():
        print("sample already drawn; samples are immutable", file=sys.stderr)
        return 1
    seen = load_sample_file(SAMPLE_FILE)
    need = DEV_SIZE + TEST_SIZE
    with get_remote_connection() as connection:
        drawn = sample_hebrew_products(
            connection,
            int(need * OVERSAMPLE),
            seed=SETSEED_VALUE,
            exclude_codes=[p.item_code for p in seen.products],
        )
    products = [SampleProduct(str(p.item_code), p.item_name) for p in drawn]
    entries, exclusions = group_products(products)
    kept = [SampleProduct(e.item_code, e.item_name) for e in entries][:need]
    if len(kept) < need:
        print(f"only {len(kept)} distinct products; need {need}", file=sys.stderr)
        return 1
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    write(SAMPLES_DIR / "dev.csv", kept[:DEV_SIZE])
    write(SAMPLES_DIR / "test.csv", kept[DEV_SIZE:])
    meta = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SPLIT_SEED,
        "postgres_setseed": SETSEED_VALUE,
        "population": "grocery.products, Hebrew letters in item_name, fee/voucher names excluded",
        "excluded_previously_inspected": len(seen.products),
        "previous_sample_sha256": seen.sha256,
        "oversampled": len(products),
        "duplicates_dropped": len(exclusions),
        "grouping_policy": GROUPING_POLICY,
        "split_rule": "drawn order is random; first 100 dev, next 100 test",
        "dev_ids_sha256": hashlib.sha256(
            ",".join(p.item_code for p in kept[:DEV_SIZE]).encode()
        ).hexdigest(),
        "test_ids_sha256": hashlib.sha256(
            ",".join(p.item_code for p in kept[DEV_SIZE:]).encode()
        ).hexdigest(),
    }
    (SAMPLES_DIR / "sample_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(f"drew {len(kept)} products; {len(exclusions)} duplicates dropped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
