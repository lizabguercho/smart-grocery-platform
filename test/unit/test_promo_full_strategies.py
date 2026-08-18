from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from src.data_extraction.models import Promotion
from src.data_extraction.parsers.promo_full import PromoFullParser
from src.database_loader.promotions_loader import PromoFullLoader


def test_promo_full_parser_delegates_to_parse_promo_full_files(
    tmp_path: Path,
) -> None:
    with patch(
        "src.data_extraction.parsers.promo_full.parse_promo_full_files",
        return_value=[],
    ) as parse_files:
        PromoFullParser().parse([tmp_path / "PromoFull.gz"])

    parse_files.assert_called_once()


def test_promo_full_loader_delegates_to_load_promotions(
    promotion: Promotion,
) -> None:
    with patch("src.database_loader.promotions_loader.load_promotions") as load:
        PromoFullLoader().load([promotion])

    load.assert_called_once_with([promotion])
