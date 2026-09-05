"""Tests for the agent model system instructions."""

from __future__ import annotations

from src.agent_platform.chat_service.instruction import (
    AGENT_INSTRUCTIONS as CHAT_SERVICE_INSTRUCTIONS,
)
from src.agent_platform.instruction import AGENT_INSTRUCTIONS


def test_agent_instructions_are_non_empty() -> None:
    assert isinstance(AGENT_INSTRUCTIONS, str)
    assert len(AGENT_INSTRUCTIONS.strip()) > 0


def test_chat_service_re_exports_same_instructions() -> None:
    assert CHAT_SERVICE_INSTRUCTIONS is AGENT_INSTRUCTIONS


def test_instructions_contain_key_operating_principles() -> None:
    # Must instruct the model to ground itself in tools, not hallucinations
    assert "tools" in AGENT_INSTRUCTIONS
    assert "load_skill" in AGENT_INSTRUCTIONS
    # Must reference the chains
    assert "Shufersal" in AGENT_INSTRUCTIONS
    assert "Rami Levy" in AGENT_INSTRUCTIONS
    assert "Victory" in AGENT_INSTRUCTIONS
    # Must handle Hebrew product names
    assert "Hebrew" in AGENT_INSTRUCTIONS
