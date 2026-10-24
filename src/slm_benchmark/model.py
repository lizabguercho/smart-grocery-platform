"""Local instruct-model interface for grocery-understanding experiments."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol

from src.product_translation.name_translator import skip_slow_packages_distributions
from src.slm_benchmark.prompt import PromptConfig

logger = logging.getLogger(__name__)

MODEL_ALIASES: dict[str, str] = {
    "qwen25_05b": "Qwen/Qwen2.5-0.5B-Instruct",
    "qwen25_15b": "Qwen/Qwen2.5-1.5B-Instruct",
}

DEFAULT_MAX_NEW_TOKENS = 256


@dataclass(frozen=True)
class ModelResponse:
    raw_text: str
    latency_seconds: float
    model_id: str


class GroceryUnderstandingModel(Protocol):
    model_id: str

    def generate(
        self, product_name: str, prompt_config: PromptConfig
    ) -> ModelResponse: ...


def resolve_model_id(model: str) -> str:
    if model in MODEL_ALIASES:
        return MODEL_ALIASES[model]
    return model


class QwenGroceryUnderstandingModel:
    """Local Qwen chat model for structured grocery-name understanding."""

    def __init__(
        self,
        model_id: str,
        *,
        max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    ) -> None:
        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self._tokenizer: Any = None
        self._model: Any = None

    def load(self) -> None:
        if self._model is not None:
            return
        logger.info("Loading local model %s ...", self.model_id)
        skip_slow_packages_distributions()
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype="auto",
            device_map="auto",
        )
        logger.info("Model ready on device %s", self._model.device)

    def generate(
        self, product_name: str, prompt_config: PromptConfig
    ) -> ModelResponse:
        name = product_name.strip()
        if not name:
            raise ValueError("Cannot run understanding on an empty product name.")

        self.load()
        messages = prompt_config.messages(name)
        prompt = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        model_inputs = self._tokenizer([prompt], return_tensors="pt").to(
            self._model.device
        )
        started = time.perf_counter()
        generated = self._model.generate(
            **model_inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
        )
        latency = time.perf_counter() - started
        new_tokens = generated[0][model_inputs["input_ids"].shape[1] :]
        raw_text = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
        return ModelResponse(
            raw_text=raw_text,
            latency_seconds=latency,
            model_id=self.model_id,
        )


def build_model(model: str, *, max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS) -> QwenGroceryUnderstandingModel:
    return QwenGroceryUnderstandingModel(
        resolve_model_id(model),
        max_new_tokens=max_new_tokens,
    )
