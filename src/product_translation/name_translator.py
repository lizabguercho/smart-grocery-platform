"""Clean model output and call a local Qwen instruct model.

The class below is a thin wrapper: load once, then translate one name
at a time. Unit tests can replace translate() with a fake so we never
download weights in CI.
"""

from __future__ import annotations

import importlib.metadata
import logging
import re
from typing import Any

from src.product_translation.config import (
    HEBREW_LETTER_RANGE,
    MAX_NEW_TOKENS,
    QWEN_MODEL_ID,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

_SURROUNDING_QUOTES = re.compile(r'^["\'«»“”]+|["\'«»“”]+$')
_LABEL_PREFIX = re.compile(
    r"^(english(?: name)?|translation|translated)\s*:\s*",
    re.IGNORECASE,
)


def contains_hebrew(text: str) -> bool:
    """True when the product name still has Hebrew letters to translate."""

    start, end = HEBREW_LETTER_RANGE
    return any(start <= ord(character) <= end for character in text)


def clean_translation(raw_text: str) -> str:
    """Turn a chat-model reply into a single supermarket-style name.

    Models sometimes add quotes, a label like "English:", or a second
    sentence. We keep the first non-empty line and strip wrapping quotes.
    """

    stripped = raw_text.strip()
    if not stripped:
        return ""

    first_line = stripped.splitlines()[0].strip()
    first_line = _SURROUNDING_QUOTES.sub("", first_line).strip()
    first_line = _LABEL_PREFIX.sub("", first_line).strip()
    first_line = _SURROUNDING_QUOTES.sub("", first_line).strip()
    return re.sub(r"\s+", " ", first_line)


def skip_slow_packages_distributions() -> None:
    """Stop Hugging Face from scanning every installed wheel on import.

    `import transformers` immediately calls
    `importlib.metadata.packages_distributions()`. That function opens
    METADATA / RECORD / top_level.txt for **every** package.

    This project's `.venv` lives under iCloud Documents. macOS File
    Provider can store those tiny files as "dataless" stubs
    (`ls -lO` shows `dataless`). Reading a stub waits for iCloud, so
    the scan looks hung. Listing distributions stays fast because it
    only reads folder names.

    Returning `{}` is safe here: transformers then falls back to a
    normal `import` when it needs an optional package version.
    """

    current = importlib.metadata.packages_distributions
    if getattr(current, "_skip_dist_info_scan", False):
        return

    def _empty_mapping() -> dict[str, list[str]]:
        return {}

    _empty_mapping._skip_dist_info_scan = True  # type: ignore[attr-defined]
    importlib.metadata.packages_distributions = _empty_mapping


class QwenProductNameTranslator:
    """Local Qwen helper: Hebrew (or mixed) grocery name → English name."""

    def __init__(self, model_id: str = QWEN_MODEL_ID) -> None:
        self.model_id = model_id
        self._tokenizer: Any = None
        self._model: Any = None

    def load(self) -> None:
        """Download (first time) and load the model into memory.

        transformers + torch live in the optional `transformers` uv group
        so everyday pytest runs do not need a multi-GB model.
        """

        if self._model is not None:
            return

        logger.info("Loading local Qwen model %s ...", self.model_id)
        skip_slow_packages_distributions()
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype="auto",
            device_map="auto",
        )
        logger.info("Qwen model ready on device %s", self._model.device)

    def translate(self, hebrew_name: str) -> str:
        """Return a concise English name, or raise if the model output is empty."""

        name = hebrew_name.strip()
        if not name:
            raise ValueError("Cannot translate an empty product name.")

        # Already-Latin names (brands, English SKUs) do not need the model.
        if not contains_hebrew(name):
            return name

        self.load()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": name},
        ]
        prompt = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        model_inputs = self._tokenizer([prompt], return_tensors="pt").to(
            self._model.device
        )
        generated = self._model.generate(
            **model_inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
        )
        # generate() returns prompt tokens + new tokens; keep only the reply.
        new_tokens = generated[0][model_inputs["input_ids"].shape[1] :]
        raw_reply = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
        english_name = clean_translation(raw_reply)
        if not english_name:
            raise ValueError(f"Qwen returned an empty translation for: {name!r}")
        return english_name
