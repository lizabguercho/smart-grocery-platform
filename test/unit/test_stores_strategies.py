from __future__ import annotations

from pathlib import Path

import pytest

from src.data_extraction.parsers.stores import StoresParser
from src.database_loader.stores_loader import StoresLoader
from src.etl.constants import STORES_NOT_IMPLEMENTED_MESSAGE


def test_stores_parser_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match=STORES_NOT_IMPLEMENTED_MESSAGE):
        StoresParser().parse([Path("Stores7290027600007-000-000-20260722-030000.gz")])


def test_stores_loader_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match=STORES_NOT_IMPLEMENTED_MESSAGE):
        StoresLoader().load([])
