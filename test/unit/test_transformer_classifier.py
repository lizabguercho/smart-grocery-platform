import pandas as pd

from src.product_classification.category_classifier import build_feature_text
from src.product_classification.transformer_classifier import (
    CATEGORIES,
    category_label_maps,
    texts_from_frame,
)


def test_every_category_gets_exactly_one_id() -> None:
    label2id, id2label = category_label_maps()
    assert set(label2id) == set(CATEGORIES)
    assert len(label2id) == len(CATEGORIES)
    assert set(id2label.values()) == set(CATEGORIES)
    assert len(id2label) == len(CATEGORIES)


def test_category_ids_are_unique() -> None:
    label2id, id2label = category_label_maps()
    assert len(set(label2id.values())) == len(label2id)
    assert len(set(id2label)) == len(id2label)
    assert set(label2id.values()) == set(id2label)


def test_category_round_trip_returns_original_name() -> None:
    label2id, id2label = category_label_maps()
    for category in CATEGORIES:
        assert id2label[label2id[category]] == category


def test_texts_from_frame_joins_name_and_manufacturer() -> None:
    frame = pd.DataFrame(
        {
            "item_name": ["חלב 3%", "חטיף במבה"],
            "manufacture_name": ["תנובה", "אוסם"],
        }
    )
    assert texts_from_frame(frame) == ["חלב 3% תנובה", "חטיף במבה אוסם"]


def test_texts_from_frame_matches_tfidf_placeholder_cleaning() -> None:
    frame = pd.DataFrame(
        {
            "item_name": ["חלב", "לחם", "מים", "עגבניה", "שוקולד"],
            "manufacture_name": [None, "-", "לא ידוע", "unknown", "  "],
        }
    )
    texts = texts_from_frame(frame)
    expected = [
        build_feature_text(name, manufacturer, include_manufacturer=True)
        for name, manufacturer in zip(frame["item_name"], frame["manufacture_name"])
    ]
    assert texts == expected
    assert texts == ["חלב", "לחם", "מים", "עגבניה", "שוקולד"]


def test_texts_from_frame_length_matches_row_count() -> None:
    frame = pd.DataFrame(
        {
            "item_name": ["a", "b", "c"],
            "manufacture_name": ["x", None, "y"],
        }
    )
    assert len(texts_from_frame(frame)) == len(frame)
