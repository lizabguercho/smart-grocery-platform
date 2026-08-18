from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.data_extraction.models import Store
from src.data_extraction.parsers.stores import StoresParser
from src.database_loader.stores_loader import StoresLoader


def test_stores_parser_delegates_to_parse_store_files(tmp_path: Path) -> None:
    with patch(
        "src.data_extraction.parsers.stores.parse_store_files",
        return_value=[],
    ) as parse_files:
        StoresParser().parse([tmp_path / "Stores.gz"])

    parse_files.assert_called_once()


def test_stores_loader_delegates_to_load_stores(store: Store) -> None:
    with patch("src.database_loader.stores_loader.load_stores") as load:
        StoresLoader().load([store])

    load.assert_called_once_with([store])
