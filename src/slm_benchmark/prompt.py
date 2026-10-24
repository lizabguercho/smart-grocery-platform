"""Versioned prompt loading for the SLM benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROMPTS_DIR = Path(__file__).with_name("prompts")


@dataclass(frozen=True)
class PromptConfig:
    version: str
    system_text: str

    def messages(self, product_name: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system_text},
            {"role": "user", "content": product_name},
        ]


def load_prompt(version: str) -> PromptConfig:
    path = PROMPTS_DIR / f"{version}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown prompt version: {version} ({path})")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Prompt file is empty: {path}")
    return PromptConfig(version=version, system_text=text)
