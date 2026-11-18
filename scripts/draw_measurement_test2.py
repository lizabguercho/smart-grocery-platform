"""Draw the NEW independent test sample (100 titles) for measurement extraction.

Read-only on REMOTE_DB_*, seeded, never touches dev.csv / test.csv. Excludes every
product in the original inspected sample, dev, and the retired first test (by code
and by folded name). Composition: 60 random titles (the representative part, used
for population claims) + 40 targeted titles that exercise what dev gold lacks:
multi-pack (N*M with unit), count plus amount, capacity container. Targeted
items are reported separately as stress strata. Strata live in a separate file so
the annotation page can show titles only.

  PYTHONPATH=. uv run python scripts/draw_measurement_test2.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import UTC, datetime

from src.database_loader.connection import get_remote_connection
from src.measurement_extraction.config import SAMPLE_FILE, SAMPLES_DIR
from src.measurement_extraction.loader import load_sample_file
from src.measurement_extraction.manifests import GROUPING_POLICY, name_key
from src.product_translation.exclusions import exclusion_like_patterns

SEED = 0.2027
QUOTAS = {"random": 60, "multipack": 15, "count_plus_amount": 15, "capacity": 10}
UNIT = r"(גר|גרם|מ.?ל|מיליליטר|ליטר|ל|ק.?ג|קילו)"
COUNT = r"(יח|יחידות|שקיות|בקבוקים|קפסולות|כוסות|מגבונים|חבילות|קופסאות)"
PATTERNS = {
    "random": r"\d",  # placeholder; random stratum also admits titles with no digit
    "multipack": rf"[0-9]+\s*[*xX×]\s*[0-9]+\s*{UNIT}",
    "count_plus_amount": rf"[0-9]+\s*{COUNT}.*[0-9]+\s*{UNIT}|[0-9]+\s*{UNIT}.*[0-9]+\s*{COUNT}",
    "capacity": r"(^|\s)(דלי|מיכל|קנקן|תרמוס|סיר|פח|כד)(\s|$).*[0-9]",
}
BASE = """
SELECT item_code::text, item_name
FROM grocery.products
WHERE item_name IS NOT NULL AND btrim(item_name) <> ''
  AND item_name ~ '[א-ת]'
  AND NOT (item_name ILIKE ANY(%s))
  AND item_code::text <> ALL(%s)
  {extra}
ORDER BY random()
LIMIT %s
"""


def read_codes_names() -> tuple[set[str], set[str]]:
    codes, names = set(), set()
    seen = load_sample_file(SAMPLE_FILE)
    rows = [(p.item_code, p.item_name) for p in seen.products]
    for split in ("dev", "test"):
        with (SAMPLES_DIR / f"{split}.csv").open(encoding="utf-8", newline="") as fh:
            rows += [(r["item_code"], r["item_name"]) for r in csv.DictReader(fh)]
    for code, name in rows:
        codes.add(code)
        names.add(name_key(name))
    return codes, names


def main() -> int:
    meta_path = SAMPLES_DIR / "test2_meta.json"
    if meta_path.exists():
        print("test2 already drawn; samples are immutable", file=sys.stderr)
        return 1
    codes, names = read_codes_names()
    chosen: list[tuple[str, str, str]] = []  # code, name, stratum
    taken_codes, taken_names = set(codes), set(names)
    shortfall: dict[str, int] = {}
    with get_remote_connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT setseed(%s)", (SEED,))
        # targeted strata first so the random part cannot crowd them out
        for stratum in ("multipack", "count_plus_amount", "capacity", "random"):
            want = QUOTAS[stratum]
            extra = "" if stratum == "random" else "AND item_name ~ %s"
            params = [exclusion_like_patterns(), sorted(taken_codes)]
            if extra:
                params.append(PATTERNS[stratum])
            params.append(int(want * 3))
            cursor.execute(BASE.format(extra=extra), params)
            got = 0
            for code, name in cursor.fetchall():
                key = name_key(name)
                if got == want or code in taken_codes or key in taken_names:
                    continue
                chosen.append((code, name, stratum))
                taken_codes.add(code)
                taken_names.add(key)
                got += 1
            if got < want:
                shortfall[stratum] = want - got
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    import random

    rng = random.Random(20271114)
    order = chosen[:]
    rng.shuffle(order)  # annotation order must not reveal the stratum
    with (SAMPLES_DIR / "test2.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["item_code", "item_name"])
        w.writerows((c, n) for c, n, _ in order)
    with (SAMPLES_DIR / "test2_strata.csv").open(
        "w", encoding="utf-8", newline=""
    ) as fh:
        w = csv.writer(fh)
        w.writerow(["item_code", "stratum"])
        w.writerows((c, s) for c, _, s in order)
    counts = {s: sum(1 for *_, x in chosen if x == s) for s in QUOTAS}
    meta = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "purpose": "new independent test set, drawn after the freeze recorded in FROZEN.md",
        "postgres_setseed": SEED,
        "shuffle_seed": 20271114,
        "quotas": QUOTAS,
        "drawn_per_stratum": counts,
        "shortfall": shortfall,
        "patterns": PATTERNS,
        "excluded": "original inspected 100, dev 100, retired test 100 (by code and folded name)",
        "grouping_policy": GROUPING_POLICY,
        "ids_sha256": hashlib.sha256(
            ",".join(c for c, _, _ in order).encode()
        ).hexdigest(),
        "guidelines": "guidelines-v2",
    }
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"drew {len(chosen)} titles: {counts}; shortfall {shortfall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
