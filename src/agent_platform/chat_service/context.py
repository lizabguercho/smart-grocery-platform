"""Control over exactly what reaches the model.

Registered on the agent as `capabilities=[ProcessHistory(...)]`. pydantic-ai
calls the processor immediately before every model request and sends whatever
it returns, so this module is the single place where the outbound context is
decided, and the single place it can be observed.

Trimming works on whole conversation turns rather than individual messages. A
turn starts at a user prompt and runs until the next one, so a tool call and
its result are always kept or dropped together. Splitting them would leave a
`ToolCallPart` with no matching `ToolReturnPart`, which model providers reject.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic_ai import RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    SystemPromptPart,
    ToolCallPart,
    UserPromptPart,
)

from src.agent_platform.chat_service.models import HistoryBudget
from src.agent_platform.chat_service.streaming import StreamingState


def _is_turn_start(message: ModelMessage) -> bool:
    """Whether this message begins a new user turn."""

    return isinstance(message, ModelRequest) and any(
        isinstance(part, UserPromptPart) for part in message.parts
    )


def _is_preamble(message: ModelMessage) -> bool:
    """Whether this message is a system preamble rather than a turn."""

    return isinstance(message, ModelRequest) and any(
        isinstance(part, SystemPromptPart) for part in message.parts
    )


def _part_characters(part: object) -> int:
    """Approximate the size of one message part, in characters."""

    total = 0
    content = getattr(part, "content", None)
    if isinstance(content, str):
        total += len(content)
    elif content is not None:
        total += len(str(content))
    if isinstance(part, ToolCallPart):
        total += len(part.args if isinstance(part.args, str) else str(part.args))
    return total


def measure_characters(messages: Sequence[ModelMessage]) -> int:
    """Approximate the size of a message list, in characters.

    Characters are a deliberately crude proxy for tokens. They need no
    provider-specific tokenizer and no network call, and the budget only has
    to bound the context, not predict billing exactly. `UsageLimits` enforces
    the real token ceiling.
    """

    return sum(_part_characters(part) for message in messages for part in message.parts)


def split_turns(
    messages: Sequence[ModelMessage],
) -> tuple[list[ModelMessage], list[list[ModelMessage]]]:
    """Split history into a system preamble and a list of whole turns."""

    preamble: list[ModelMessage] = []
    turns: list[list[ModelMessage]] = []
    current: list[ModelMessage] = []

    for message in messages:
        if not turns and not current and _is_preamble(message):
            preamble.append(message)
            continue
        if _is_turn_start(message) and current:
            turns.append(current)
            current = []
        current.append(message)

    if current:
        turns.append(current)
    return preamble, turns


def trim_history(
    messages: Sequence[ModelMessage], budget: HistoryBudget
) -> list[ModelMessage]:
    """Drop the oldest whole turns until the history fits the budget.

    The most recent turn is always kept, even when it alone exceeds the
    budget: sending no user prompt at all would be worse than sending an
    oversized one, and `UsageLimits` still caps the run.
    """

    preamble, turns = split_turns(messages)
    if not turns:
        return list(preamble)

    kept: list[list[ModelMessage]] = []
    message_count = len(preamble)
    character_count = measure_characters(preamble)

    for turn in reversed(turns):
        turn_messages = len(turn)
        turn_characters = measure_characters(turn)
        exceeds_budget = (
            message_count + turn_messages > budget.max_messages
            or character_count + turn_characters > budget.max_characters
        )
        if kept and exceeds_budget:
            break
        kept.append(turn)
        message_count += turn_messages
        character_count += turn_characters

    trimmed: list[ModelMessage] = list(preamble)
    for turn in reversed(kept):
        trimmed.extend(turn)
    return trimmed


def _resolved_instructions(messages: Sequence[ModelMessage]) -> str | None:
    """Return the instructions attached to the outgoing request, if any.

    Instructions live on `ModelRequest.instructions` rather than in `parts`,
    and are re-resolved by the agent on every request, so they are read from
    the final request instead of being carried in history.
    """

    for message in reversed(messages):
        if isinstance(message, ModelRequest) and message.instructions:
            return message.instructions
    return None


def build_history_processor(budget: HistoryBudget, state: StreamingState):
    """Build the history processor for one run.

    The returned function both shapes the outbound context and records it on
    `state`, so `state.model_requests` ends up holding the exact payload of
    every request the run made.
    """

    async def process_history(
        ctx: RunContext, messages: list[ModelMessage]
    ) -> list[ModelMessage]:
        trimmed = trim_history(messages, budget)
        state.record_model_request(
            run_step=ctx.run_step,
            messages=trimmed,
            instructions=_resolved_instructions(trimmed),
        )
        return trimmed

    return process_history
