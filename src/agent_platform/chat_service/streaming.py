"""The streamed wire format and the state accumulated during a run.

`StreamEvent` is deliberately our own type rather than pydantic-ai's event
union: the service maps provider events onto it, so the client contract stays
stable across pydantic-ai upgrades.

`StreamingState` is the single object threaded through a run. Anything a caller
might want to know afterwards, including the exact payloads sent to the model,
lives on it rather than being passed around as loose arguments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Literal

import pydantic
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import RunUsage

from src.agent_platform.chat_service.models import (
    AgentConfig,
    AgentRequest,
    AgentStatus,
    StreamEventType,
    ToolCallRecord,
)
from src.agent_platform.errors import ChatErrorPayload, ChatServiceError

ILLEGAL_TRANSITION_MESSAGE = "Cannot move from terminal status {current} to {target}."


class StatusEvent(pydantic.BaseModel):
    """The run entered a new lifecycle status.

    Carries the identifiers so the first event of a stream already tells a
    client which conversation to continue, without waiting for the run to
    succeed.
    """

    type: Literal[StreamEventType.STATUS] = StreamEventType.STATUS
    status: AgentStatus
    query_id: str
    conversation_id: str


class TextDeltaEvent(pydantic.BaseModel):
    """An incremental piece of the assistant's answer."""

    type: Literal[StreamEventType.TEXT_DELTA] = StreamEventType.TEXT_DELTA
    delta: str


class ToolCallEvent(pydantic.BaseModel):
    """The model decided to call one of the platform's tools."""

    type: Literal[StreamEventType.TOOL_CALL] = StreamEventType.TOOL_CALL
    tool_call_id: str
    tool_name: str
    arguments: str


class ToolResultEvent(pydantic.BaseModel):
    """A tool returned, and this is what the model will see."""

    type: Literal[StreamEventType.TOOL_RESULT] = StreamEventType.TOOL_RESULT
    tool_call_id: str
    tool_name: str
    result: str


class UsageEvent(pydantic.BaseModel):
    """Token and request counts accumulated so far."""

    type: Literal[StreamEventType.USAGE] = StreamEventType.USAGE
    requests: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ErrorEvent(pydantic.BaseModel):
    """A terminal failure. No further events follow."""

    type: Literal[StreamEventType.ERROR] = StreamEventType.ERROR
    error: ChatErrorPayload


class CompletedEvent(pydantic.BaseModel):
    """The run finished successfully. Carries the full collected answer."""

    type: Literal[StreamEventType.COMPLETED] = StreamEventType.COMPLETED
    query_id: str
    conversation_id: str
    text: str


StreamEvent = Annotated[
    StatusEvent
    | TextDeltaEvent
    | ToolCallEvent
    | ToolResultEvent
    | UsageEvent
    | ErrorEvent
    | CompletedEvent,
    pydantic.Field(discriminator="type"),
]


@dataclass(frozen=True)
class ModelRequestAudit:
    """Exactly what was sent to the model on one request.

    Recorded by the history processor, which runs immediately before each model
    request and whose return value is what actually goes on the wire. Keeping
    the resolved messages here is what makes the context auditable at any point
    during a run.
    """

    run_step: int
    recorded_at: datetime
    messages: list[ModelMessage]
    instructions: str | None

    @property
    def message_count(self) -> int:
        """Number of messages that reached the model on this request."""

        return len(self.messages)


@dataclass
class StreamingState:
    """Mutable state of one agent run.

    Created before the agent is built, so the history processor and the event
    mapper can both write to it while the run streams.
    """

    request: AgentRequest
    config: AgentConfig
    status: AgentStatus = AgentStatus.PENDING
    text: str = ""
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    usage: RunUsage | None = None
    error: ChatServiceError | None = None
    model_requests: list[ModelRequestAudit] = field(default_factory=list)

    def transition(self, target: AgentStatus) -> StatusEvent:
        """Move to `target` and return the event announcing it.

        Raises:
            ValueError: If the run already reached a terminal status.
        """

        if self.status.is_terminal:
            raise ValueError(
                ILLEGAL_TRANSITION_MESSAGE.format(
                    current=self.status.value, target=target.value
                )
            )
        self.status = target
        return StatusEvent(
            status=target,
            query_id=self.request.query_id,
            conversation_id=self.request.conversation_id,
        )

    def append_text(self, delta: str) -> TextDeltaEvent:
        """Accumulate an answer fragment and return the event for it."""

        self.text += delta
        return TextDeltaEvent(delta=delta)

    def record_tool_call(
        self, tool_call_id: str, tool_name: str, arguments: str
    ) -> ToolCallEvent:
        """Record a tool invocation and return the event for it."""

        self.tool_calls.append(
            ToolCallRecord(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                arguments=arguments,
            )
        )
        return ToolCallEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            arguments=arguments,
        )

    def record_tool_result(
        self, tool_call_id: str, tool_name: str, result: str
    ) -> ToolResultEvent:
        """Attach a result to a recorded call and return the event for it."""

        for index, call in enumerate(self.tool_calls):
            if call.tool_call_id == tool_call_id and call.result is None:
                self.tool_calls[index] = ToolCallRecord(
                    tool_call_id=call.tool_call_id,
                    tool_name=call.tool_name,
                    arguments=call.arguments,
                    result=result,
                )
                break
        return ToolResultEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            result=result,
        )

    def record_model_request(
        self, run_step: int, messages: list[ModelMessage], instructions: str | None
    ) -> None:
        """Audit one outbound model request."""

        self.model_requests.append(
            ModelRequestAudit(
                run_step=run_step,
                recorded_at=datetime.now(UTC),
                messages=list(messages),
                instructions=instructions,
            )
        )

    def record_usage(self, usage: RunUsage) -> UsageEvent:
        """Store the latest usage snapshot and return the event for it."""

        self.usage = usage
        return UsageEvent(
            requests=usage.requests,
            tool_calls=usage.tool_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
        )

    def fail(self, error: ChatServiceError, status: AgentStatus) -> ErrorEvent:
        """Record a terminal failure and return the event for it.

        The status is set directly rather than through `transition` so that a
        failure is always recordable, including after the run already ended.
        """

        self.error = error
        self.status = status
        return ErrorEvent(error=error.to_payload())

    def complete(self) -> CompletedEvent:
        """Return the terminal success event for this run."""

        return CompletedEvent(
            query_id=self.request.query_id,
            conversation_id=self.request.conversation_id,
            text=self.text,
        )
