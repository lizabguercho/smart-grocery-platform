"""Records exchanged by the chat service.

Following CONTRIBUTING.md: Pydantic models sit at the untrusted HTTP boundary
(`ChatInput`, `ChatOutput`), dataclasses carry internal records the process
already trusts, and closed vocabularies are enums.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import pydantic
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits

MAX_MESSAGE_LENGTH = 8000


class AgentStatus(Enum):
    """Lifecycle of a single agent run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    INTERRUPTED = "interrupted"
    ABORTED = "aborted"

    @property
    def is_terminal(self) -> bool:
        """Whether no further transition out of this status is allowed."""

        return self is not AgentStatus.PENDING and self is not AgentStatus.RUNNING


class StreamEventType(str, Enum):
    """Discriminator for the events the service streams to a client."""

    STATUS = "status"
    TEXT_DELTA = "text_delta"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    USAGE = "usage"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass(frozen=True)
class AgentConfig:
    """Model selection and sampling settings for a run."""

    model: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    def to_model_settings(self) -> ModelSettings:
        """Map this config onto pydantic-ai's `ModelSettings`.

        The mapping is explicit rather than a dict splat because `ModelSettings`
        has no `model` key: the model string is a constructor argument to
        `Agent`, not a per-request setting.
        """

        return ModelSettings(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
        )


@dataclass(frozen=True)
class UsageBudget:
    """Per-run ceiling on what a single question may cost."""

    request_limit: int
    tool_calls_limit: int
    total_tokens_limit: int

    def to_usage_limits(self) -> UsageLimits:
        """Map this budget onto pydantic-ai's `UsageLimits`."""

        return UsageLimits(
            request_limit=self.request_limit,
            tool_calls_limit=self.tool_calls_limit,
            total_tokens_limit=self.total_tokens_limit,
        )


@dataclass(frozen=True)
class RateLimitPolicy:
    """Token bucket shape for incoming chat requests."""

    requests_per_minute: int
    burst: int

    @property
    def refill_per_second(self) -> float:
        """Tokens added to the bucket each second."""

        return self.requests_per_minute / 60.0


@dataclass(frozen=True)
class HistoryBudget:
    """How much conversation history may reach the model on one request."""

    max_messages: int
    max_characters: int


@dataclass(frozen=True)
class AgentRequest:
    """A chat request resolved against a conversation, ready for the agent."""

    query_id: str
    conversation_id: str
    message: str
    is_new_conversation: bool
    context: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class Conversation:
    """A chat thread and the model messages recorded against it."""

    id: str
    created_at: datetime
    title: str | None = None


@dataclass(frozen=True)
class ToolCallRecord:
    """A tool invocation observed during a run, and its result once known."""

    tool_call_id: str
    tool_name: str
    arguments: str
    result: str | None = None


class ChatInput(pydantic.BaseModel):
    """Incoming chat request. Untrusted, so validated by Pydantic."""

    model_config = pydantic.ConfigDict(extra="forbid")

    message: str = pydantic.Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    conversation_id: str | None = None
    context: dict[str, str] = pydantic.Field(default_factory=dict)
    metadata: dict[str, str] = pydantic.Field(default_factory=dict)


class ChatOutput(pydantic.BaseModel):
    """Non-streaming response: the collected result of one run."""

    query_id: str
    conversation_id: str
    status: AgentStatus
    text: str
    tool_calls: list[str] = pydantic.Field(default_factory=list)
