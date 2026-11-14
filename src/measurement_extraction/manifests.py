"""Frozen development/test manifests with a documented grouping policy.

Grouping policy: records sharing an item_code, or an identical name after
whitespace/quote folding, form one group. Digits are never folded, so pack
sizes and variants stay distinct.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from src.measurement_extraction.config import DEV_SIZE, SPLIT_SEED
from src.measurement_extraction.loader import SampleFile, SampleProduct

_FOLD = re.compile(r"[\s\"'`״׳]+")


def name_key(name: str) -> str:
    return _FOLD.sub("", name).lower()


@dataclass(frozen=True)
class ManifestEntry:
    item_code: str
    item_name: str
    group_id: str


@dataclass
class Manifest:
    split: str
    seed: int
    source_sha256: str
    created_at: str
    grouping_policy: str
    selection_rule: str
    entries: list[ManifestEntry]
    exclusions: list[dict] = field(default_factory=list)
    shortfall: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


GROUPING_POLICY = "same item_code or identical name after whitespace/quote folding"


def group_products(
    products: list[SampleProduct],
) -> tuple[list[ManifestEntry], list[dict]]:
    """Drop exact duplicates, then assign each distinct group one kept record."""

    kept: list[ManifestEntry] = []
    exclusions: list[dict] = []
    code_group: dict[str, str] = {}
    name_group: dict[str, str] = {}
    for product in products:
        key = name_key(product.item_name)
        group = code_group.get(product.item_code) or name_group.get(key)
        if group is not None:
            exclusions.append(
                {
                    "item_code": product.item_code,
                    "reason": f"duplicate of group {group}",
                }
            )
            continue
        group = product.item_code
        code_group[product.item_code] = name_group[key] = group
        kept.append(ManifestEntry(product.item_code, product.item_name, group))
    return kept, exclusions


def build_dev_manifest(
    sample: SampleFile, size: int = DEV_SIZE, seed: int = SPLIT_SEED
) -> Manifest:
    entries, exclusions = group_products(sample.products)
    rule = "all independent groups in file order"
    if len(entries) > size:
        entries = sorted(
            random.Random(seed).sample(entries, size), key=lambda e: e.item_code
        )
        rule = f"deterministic random.Random({seed}).sample of {size} groups, sorted by item_code"
    return Manifest(
        split="dev",
        seed=seed,
        source_sha256=sample.sha256,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        grouping_policy=GROUPING_POLICY,
        selection_rule=rule,
        entries=entries,
        exclusions=exclusions,
        shortfall=max(0, size - len(entries)),
    )


def assert_no_leakage(dev: Manifest, test: Manifest) -> None:
    """Raise if any group or code appears in both splits."""

    overlap = {e.group_id for e in dev.entries} & {e.group_id for e in test.entries}
    overlap |= {e.item_code for e in dev.entries} & {e.item_code for e in test.entries}
    overlap |= {name_key(e.item_name) for e in dev.entries} & {
        name_key(e.item_name) for e in test.entries
    }
    if overlap:
        raise ValueError(f"dev/test leakage: {sorted(overlap)[:5]}")
