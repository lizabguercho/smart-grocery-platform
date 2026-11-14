"""Load the raw product sample file without altering IDs or Hebrew text."""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

HEADER = ("item_code", "item_name")


@dataclass(frozen=True)
class SampleProduct:
    item_code: str
    item_name: str


@dataclass(frozen=True)
class SampleFile:
    products: list[SampleProduct]
    sha256: str
    had_header: bool


def load_sample_file(path: Path) -> SampleFile:
    """Parse a 2-column CSV (header optional); IDs stay strings."""

    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    had_header = bool(rows) and tuple(rows[0]) == HEADER
    if had_header:
        rows = rows[1:]
    products = []
    for number, row in enumerate(rows, start=1):
        if len(row) != 2:
            raise ValueError(f"row {number}: expected 2 columns, got {len(row)}")
        products.append(SampleProduct(item_code=row[0], item_name=row[1]))
    return SampleFile(products, hashlib.sha256(raw).hexdigest(), had_header)
