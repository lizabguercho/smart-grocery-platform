"""Errors raised by the agent platform.

Every failure the chat service can report is a `ChatServiceError` subclass. The
subclass owns its `ErrorCode` and HTTP status, so callers raise a named
exception instead of assembling a code, a status and a message by hand and
passing them down through the service, the stream and the HTTP layer.

`ChatErrorPayload` is the single wire representation. Both the HTTP error
response and the SSE `error` event serialize the same payload.
"""

from __future__ import annotations

from enum import Enum

import pydantic

HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_CLIENT_CLOSED_REQUEST = 499
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_BAD_GATEWAY = 502
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_TOO_MANY_REQUESTS = 429


class ErrorCode(str, Enum):
    """Stable identifiers a client can branch on."""

    INVALID_REQUEST = "invalid_request"
    CONVERSATION_NOT_FOUND = "conversation_not_found"
    RATE_LIMITED = "rate_limited"
    USAGE_LIMIT_EXCEEDED = "usage_limit_exceeded"
    MODEL_UNAVAILABLE = "model_unavailable"
    DATABASE_UNAVAILABLE = "database_unavailable"
    SKILL_LOAD_FAILED = "skill_load_failed"
    CANCELLED = "cancelled"
    INTERNAL = "internal"


class ChatErrorPayload(pydantic.BaseModel):
    """Serialized form of a `ChatServiceError`, shared by HTTP and SSE."""

    code: ErrorCode
    message: str
    retry_after_seconds: float | None = None


class ChatServiceError(Exception):
    """Base class for every error the chat service reports to a client.

    Subclasses set `code` and `http_status` as class attributes. `retry_after`
    is only meaningful for transient failures.
    """

    code: ErrorCode = ErrorCode.INTERNAL
    http_status: int = HTTP_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after

    def to_payload(self) -> ChatErrorPayload:
        """Return the wire representation of this error."""

        return ChatErrorPayload(
            code=self.code,
            message=self.message,
            retry_after_seconds=self.retry_after,
        )


class InvalidChatRequestError(ChatServiceError):
    """The incoming request is well-formed JSON but not a usable chat request."""

    code = ErrorCode.INVALID_REQUEST
    http_status = HTTP_BAD_REQUEST


class ConversationNotFoundError(ChatServiceError):
    """The requested conversation id is unknown to the conversation store."""

    code = ErrorCode.CONVERSATION_NOT_FOUND
    http_status = HTTP_NOT_FOUND


class RateLimitExceededError(ChatServiceError):
    """The caller sent more requests than the rate limit policy allows."""

    code = ErrorCode.RATE_LIMITED
    http_status = HTTP_TOO_MANY_REQUESTS


class UsageLimitError(ChatServiceError):
    """The run hit the per-run token, request or tool-call ceiling."""

    code = ErrorCode.USAGE_LIMIT_EXCEEDED
    http_status = HTTP_BAD_REQUEST


class ModelUnavailableError(ChatServiceError):
    """The model provider rejected the request or could not be reached."""

    code = ErrorCode.MODEL_UNAVAILABLE
    http_status = HTTP_BAD_GATEWAY


class DatabaseUnavailableError(ChatServiceError):
    """A SQL tool could not reach the database or its query failed."""

    code = ErrorCode.DATABASE_UNAVAILABLE
    http_status = HTTP_SERVICE_UNAVAILABLE


class SkillLoadError(ChatServiceError):
    """The skills directory could not be discovered or parsed."""

    code = ErrorCode.SKILL_LOAD_FAILED
    http_status = HTTP_INTERNAL_SERVER_ERROR


class RunCancelledError(ChatServiceError):
    """The client disconnected or the run was cancelled before completing."""

    code = ErrorCode.CANCELLED
    http_status = HTTP_CLIENT_CLOSED_REQUEST


class InternalChatServiceError(ChatServiceError):
    """An unexpected failure, reported without leaking internals to the client."""

    code = ErrorCode.INTERNAL
    http_status = HTTP_INTERNAL_SERVER_ERROR


ERROR_TYPES: tuple[type[ChatServiceError], ...] = (
    InvalidChatRequestError,
    ConversationNotFoundError,
    RateLimitExceededError,
    UsageLimitError,
    ModelUnavailableError,
    DatabaseUnavailableError,
    SkillLoadError,
    RunCancelledError,
    InternalChatServiceError,
)

_ERROR_TYPES_BY_CODE: dict[ErrorCode, type[ChatServiceError]] = {
    error_type.code: error_type for error_type in ERROR_TYPES
}


def error_from_payload(payload: ChatErrorPayload) -> ChatServiceError:
    """Rebuild the exception a payload was produced from.

    Lets the non-streaming route re-raise the failure its streaming
    counterpart reported, without either side hand-mapping codes.
    """

    error_type = _ERROR_TYPES_BY_CODE.get(payload.code, InternalChatServiceError)
    return error_type(payload.message, retry_after=payload.retry_after_seconds)
