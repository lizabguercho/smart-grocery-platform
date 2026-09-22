"""Hugging Face transformer experiments for SuperCompare main categories.

Label IDs are fixed from CATEGORIES so later training does not invent a
mapping from a train/validation/test split.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from src.product_classification.category_classifier import build_feature_text

ALEPHBERT_MODEL_ID = "onlplab/alephbert-base"

# SuperCompare's 12 main categories. Order is the ID order (0 .. 11).
CATEGORIES: tuple[str, ...] = (
    "Baby",
    "Bakery",
    "Beverages",
    "Dairy & Eggs",
    "Deli & Salads",
    "Fresh Produce",
    "Frozen",
    "Household & Cleaning",
    "Meat & Fish",
    "Pantry & Cooking",
    "Personal Care & Hygiene",
    "Snacks & Sweets",
)


def category_label_maps() -> tuple[dict[str, int], dict[int, str]]:
    """Return name→id and id→name maps from CATEGORIES order only."""

    label2id = {category: index for index, category in enumerate(CATEGORIES)}
    id2label = {index: category for category, index in label2id.items()}
    return label2id, id2label


def texts_from_frame(frame: pd.DataFrame) -> list[str]:
    """One item_name + manufacture_name string per row, same cleaning as TF-IDF."""

    return [
        build_feature_text(
            row.item_name,
            row.manufacture_name,
            include_manufacturer=True,
        )
        for row in frame.itertuples(index=False)
    ]


def print_alephbert_tokenizer_demo(texts: Sequence[str]) -> None:
    """Load the AlephBERT tokenizer only and print encodings for sample texts.

    This is a read-only demo. It does not load a classification head and
    does not train.
    """

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(ALEPHBERT_MODEL_ID)
    print(f"Tokenizer: {ALEPHBERT_MODEL_ID}", flush=True)
    print(f"Vocab size: {tokenizer.vocab_size}", flush=True)
    for index, text in enumerate(texts, start=1):
        encoded = tokenizer(text)
        tokens = tokenizer.convert_ids_to_tokens(encoded["input_ids"])
        print(f"\n--- sample {index} ---", flush=True)
        print(f"text:            {text}", flush=True)
        print(f"tokens:          {tokens}", flush=True)
        print(f"input_ids:       {encoded['input_ids']}", flush=True)
        print(f"attention_mask:  {encoded['attention_mask']}", flush=True)
