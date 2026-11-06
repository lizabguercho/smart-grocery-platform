"""System B: Qwen3.5-4B (non-thinking, greedy, one attempt per title)."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Self

from src.measurement_extraction.prompts import SYSTEM_PROMPT
from src.measurement_extraction.schema import Annotation, Measurement
from src.measurement_extraction.units import apply_canonical

MODEL_ID = "Qwen/Qwen3.5-4B"
MODEL_REVISION = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
MAX_NEW_TOKENS = 256
# Uniform 4-bit (group size 64) MLX conversion of the pinned checkpoint above,
# made locally with: mlx_lm convert -q --q-bits 4 --q-group-size 64
MLX_MODEL_PATH = Path.home() / ".cache" / "mlx_models" / "Qwen3.5-4B-4bit-g64"
MLX_DESCRIPTION = (
    f"{MODEL_ID}@{MODEL_REVISION[:7]} -> local MLX 4-bit, group 64 (mlx-lm 0.32.2)"
)
ALLOWED = {
    "source_text",
    "source_amount",
    "source_unit",
    "describes",
    "measurement_role",
    "amount_scope",
    "package_count",
    "counted_item",
}


@dataclass
class QwenOutput:
    annotation: Annotation | None
    status: str  # ok | invalid_json | invalid_schema | truncated
    raw: str
    ungrounded: list[str]
    seconds: float
    new_tokens: int
    batch_size: int = 1


class QwenExtractor:
    def __init__(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._torch = torch
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, padding_side="left"
        )
        self.model = (
            AutoModelForCausalLM.from_pretrained(
                MODEL_ID, revision=MODEL_REVISION, dtype=torch.bfloat16
            )
            .to(self.device)
            .eval()
        )

    def extract(self, title: str) -> QwenOutput:
        return self.extract_batch([title])[0]

    def extract_batch(self, titles: list[str]) -> list[QwenOutput]:
        """One generate call for several titles (left-padded, greedy, one attempt each)."""

        texts = [
            self.tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Title: {title}"},
                ],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            for title in titles
        ]
        inputs = self.tokenizer(texts, return_tensors="pt", padding=True).to(
            self.device
        )
        started = time.perf_counter()
        with self._torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False
            )
        seconds = time.perf_counter() - started
        eos = self.tokenizer.convert_tokens_to_ids("<|im_end|>")
        results = []
        for title, row in zip(titles, out[:, inputs["input_ids"].shape[1] :]):
            ids = row.tolist()
            finished = eos in ids
            ids = ids[: ids.index(eos)] if finished else ids
            raw = self.tokenizer.decode(ids, skip_special_tokens=True)
            status = "ok" if finished else "truncated"
            annotation, status, ungrounded = parse_output(raw, title, status)
            results.append(
                QwenOutput(
                    annotation,
                    status,
                    raw,
                    ungrounded,
                    seconds / len(titles),
                    len(ids),
                    len(titles),
                )
            )
        return results


class MlxQwenExtractor:
    """Same interface as QwenExtractor, on the 4-bit MLX conversion (much faster on Apple Silicon)."""

    device = "mlx"

    def __init__(self) -> None:
        from mlx_lm import load

        self.model, self.tokenizer = load(str(MLX_MODEL_PATH))

    def extract(self, title: str) -> QwenOutput:
        return self.extract_batch([title])[0]

    def extract_batch(self, titles: list[str]) -> list[QwenOutput]:
        from mlx_lm.generate import batch_generate

        prompts = [
            self.tokenizer.encode(
                self.tokenizer.apply_chat_template(
                    [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Title: {title}"},
                    ],
                    add_generation_prompt=True,
                    enable_thinking=False,
                    tokenize=False,
                )
            )
            for title in titles
        ]
        started = time.perf_counter()
        # Greedy is mlx-lm's default sampler (temperature 0).
        response = batch_generate(
            self.model, self.tokenizer, prompts=prompts, max_tokens=MAX_NEW_TOKENS
        )
        seconds = time.perf_counter() - started
        results = []
        for title, raw in zip(titles, response.texts):
            tokens = len(self.tokenizer.encode(raw))
            status = "truncated" if tokens >= MAX_NEW_TOKENS - 1 else "ok"
            annotation, status, ungrounded = parse_output(raw, title, status)
            results.append(
                QwenOutput(
                    annotation,
                    status,
                    raw,
                    ungrounded,
                    seconds / len(titles),
                    tokens,
                    len(titles),
                )
            )
        return results


class BatchWorker:
    """One model instance behind an asyncio queue.

    Callers `await submit(title)`; a single worker gathers whatever is waiting
    (up to max_batch) into one generate call and resolves each caller's future.
    """

    def __init__(
        self,
        extractor: QwenExtractor | MlxQwenExtractor,
        max_batch: int,
        max_wait: float = 0.05,
    ) -> None:
        self._extractor = extractor
        self._max_batch = max_batch
        self._max_wait = max_wait
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def __aenter__(self) -> Self:
        self._task = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, *exc) -> None:
        self._task.cancel()

    async def submit(self, title: str) -> QwenOutput:
        future = asyncio.get_running_loop().create_future()
        await self._queue.put((title, future))
        return await future

    async def _run(self) -> None:
        while True:
            batch = [await self._queue.get()]
            deadline = time.monotonic() + self._max_wait
            while (
                len(batch) < self._max_batch
                and (left := deadline - time.monotonic()) > 0
            ):
                try:
                    batch.append(await asyncio.wait_for(self._queue.get(), left))
                except TimeoutError:
                    break
            try:
                outputs = await asyncio.to_thread(
                    self._extractor.extract_batch, [title for title, _ in batch]
                )
                for (_, future), output in zip(batch, outputs):
                    future.set_result(output)
            except Exception as error:  # noqa: BLE001 - a failed batch must not hang its callers
                for _, future in batch:
                    future.set_exception(error)


def parse_output(
    raw: str, title: str, status: str = "ok"
) -> tuple[Annotation | None, str, list[str]]:
    """Parse one response. Failures are returned as statuses, never as 'no measurement'."""

    if status == "truncated":
        return None, "truncated", []
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else None
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict):
        return None, "invalid_json", []
    try:
        entries = []
        for item in data.get("measurements") or []:
            fields = {k: v for k, v in item.items() if k in ALLOWED}
            for key in ("source_amount",):
                if fields.get(key) is not None:
                    fields[key] = Decimal(str(fields[key]).replace(",", "."))
            entries.append(apply_canonical(Measurement.model_validate(fields)))
        annotation = Annotation(
            has_measurement=bool(data.get("has_measurement")), measurements=entries
        )
    except (ValueError, TypeError, AttributeError, ArithmeticError):
        return None, "invalid_schema", []
    ungrounded = [
        e.source_text for e in entries if e.source_text and e.source_text not in title
    ]
    return annotation, "ok", ungrounded
