"""Tests for outbound context control.

The load-bearing property is that trimming never separates a `ToolCallPart`
from its `ToolReturnPart`, because model providers reject a tool call with no
matching result.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from src.agent_platform.chat_service.context import (
    build_history_processor,
    measure_characters,
    split_turns,
    trim_history,
)
from src.agent_platform.chat_service.models import (
    AgentConfig,
    AgentRequest,
    HistoryBudget,
)
from src.agent_platform.chat_service.streaming import StreamingState

GENEROUS_BUDGET = HistoryBudget(max_messages=100, max_characters=100_000)
TOOL_CALL_ID = "call-1"


def plain_turn(question: str, answer: str) -> list[ModelMessage]:
    """A turn with no tool use."""

    return [
        ModelRequest(parts=[UserPromptPart(content=question)]),
        ModelResponse(parts=[TextPart(content=answer)]),
    ]


def tool_turn(question: str, answer: str) -> list[ModelMessage]:
    """A turn where the model called a tool before answering."""

    return [
        ModelRequest(parts=[UserPromptPart(content=question)]),
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="cheapest_chain_summary",
                    args={},
                    tool_call_id=TOOL_CALL_ID,
                )
            ]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="cheapest_chain_summary",
                    content="summary",
                    tool_call_id=TOOL_CALL_ID,
                )
            ]
        ),
        ModelResponse(parts=[TextPart(content=answer)]),
    ]


def tool_call_ids(messages: list[ModelMessage]) -> set[str]:
    return {
        part.tool_call_id
        for message in messages
        for part in message.parts
        if isinstance(part, ToolCallPart)
    }


def tool_return_ids(messages: list[ModelMessage]) -> set[str]:
    return {
        part.tool_call_id
        for message in messages
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    }


def make_state() -> StreamingState:
    return StreamingState(
        request=AgentRequest(
            query_id="query-1",
            conversation_id="conversation-1",
            message="hello",
            is_new_conversation=True,
        ),
        config=AgentConfig(
            model="openai:gpt-5.2", temperature=0.0, max_tokens=10, top_p=1.0
        ),
    )


class StubRunStep:
    """Minimal stand-in for `RunContext`, which only `run_step` is read from."""

    run_step = 3


def test_split_turns_groups_each_user_prompt_with_its_response() -> None:
    messages = plain_turn("first", "one") + plain_turn("second", "two")

    preamble, turns = split_turns(messages)

    assert preamble == []
    assert len(turns) == 2
    assert len(turns[0]) == 2


def test_split_turns_keeps_tool_traffic_inside_its_turn() -> None:
    messages = plain_turn("first", "one") + tool_turn("second", "two")

    _, turns = split_turns(messages)

    assert len(turns) == 2
    assert len(turns[1]) == 4


def test_split_turns_separates_a_system_preamble() -> None:
    messages = [
        ModelRequest(parts=[SystemPromptPart(content="be helpful")]),
        *plain_turn("first", "one"),
    ]

    preamble, turns = split_turns(messages)

    assert len(preamble) == 1
    assert len(turns) == 1


def test_trim_keeps_everything_within_budget() -> None:
    messages = plain_turn("first", "one") + plain_turn("second", "two")

    assert trim_history(messages, GENEROUS_BUDGET) == messages


def test_trim_drops_the_oldest_turn_first() -> None:
    messages = plain_turn("oldest", "one") + plain_turn("newest", "two")

    trimmed = trim_history(
        messages, HistoryBudget(max_messages=2, max_characters=10_000)
    )

    assert len(trimmed) == 2
    assert trimmed == messages[2:]


def test_trim_never_splits_a_tool_call_from_its_result() -> None:
    messages = plain_turn("older", "one") + tool_turn("newer", "two")

    # A three-message budget cannot fit the four-message tool turn, so a
    # naive tail slice would cut the ToolCallPart and keep its ToolReturnPart.
    trimmed = trim_history(
        messages, HistoryBudget(max_messages=3, max_characters=10_000)
    )

    assert tool_call_ids(trimmed) == tool_return_ids(trimmed)


def test_trim_always_keeps_the_most_recent_turn() -> None:
    messages = tool_turn("only", "answer")

    trimmed = trim_history(messages, HistoryBudget(max_messages=1, max_characters=1))

    assert trimmed == messages


def test_trim_respects_the_character_budget() -> None:
    messages = plain_turn("x" * 500, "y" * 500) + plain_turn("short", "answer")

    trimmed = trim_history(
        messages, HistoryBudget(max_messages=100, max_characters=200)
    )

    assert len(trimmed) == 2
    assert trimmed == messages[2:]


def test_trim_preserves_a_system_preamble_it_cannot_drop() -> None:
    preamble = ModelRequest(parts=[SystemPromptPart(content="be helpful")])
    messages = [preamble, *plain_turn("old", "one"), *plain_turn("new", "two")]

    trimmed = trim_history(
        messages, HistoryBudget(max_messages=3, max_characters=10_000)
    )

    assert trimmed[0] is preamble


def test_measure_characters_counts_tool_arguments() -> None:
    with_args = [
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="find_products",
                    args={"name_query": "milk"},
                    tool_call_id=TOOL_CALL_ID,
                )
            ]
        )
    ]

    assert measure_characters(with_args) > 0


def test_measure_characters_of_nothing_is_zero() -> None:
    assert measure_characters([]) == 0


@pytest.mark.anyio
async def test_processor_records_what_it_sent() -> None:
    state = make_state()
    processor = build_history_processor(GENEROUS_BUDGET, state)
    messages = plain_turn("first", "one")

    returned = await processor(StubRunStep(), messages)

    assert returned == messages
    assert len(state.model_requests) == 1
    audit = state.model_requests[0]
    assert audit.run_step == 3
    assert audit.message_count == 2
    assert isinstance(audit.recorded_at, datetime)
    assert audit.recorded_at.tzinfo is UTC


@pytest.mark.anyio
async def test_processor_audits_the_trimmed_list_not_the_original() -> None:
    state = make_state()
    processor = build_history_processor(
        HistoryBudget(max_messages=2, max_characters=10_000), state
    )
    messages = plain_turn("oldest", "one") + plain_turn("newest", "two")

    returned = await processor(StubRunStep(), messages)

    # The audit must reflect the wire payload, so it can be trusted as a
    # record of what the model actually saw.
    assert state.model_requests[0].messages == returned
    assert state.model_requests[0].message_count == 2


@pytest.mark.anyio
async def test_processor_records_one_audit_per_request() -> None:
    state = make_state()
    processor = build_history_processor(GENEROUS_BUDGET, state)

    await processor(StubRunStep(), plain_turn("first", "one"))
    await processor(StubRunStep(), plain_turn("second", "two"))

    assert len(state.model_requests) == 2
