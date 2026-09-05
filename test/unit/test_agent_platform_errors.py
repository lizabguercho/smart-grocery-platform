"""Tests for the chat service error hierarchy."""

from __future__ import annotations

import pytest

from src.agent_platform.errors import (
    ERROR_TYPES,
    HTTP_NOT_FOUND,
    HTTP_TOO_MANY_REQUESTS,
    ChatErrorPayload,
    ChatServiceError,
    ConversationNotFoundError,
    DatabaseUnavailableError,
    ErrorCode,
    RateLimitExceededError,
    error_from_payload,
)


def test_every_error_carries_its_own_code_and_status() -> None:
    for error_type in ERROR_TYPES:
        assert isinstance(error_type.code, ErrorCode)
        assert error_type.http_status >= 400


def test_error_codes_are_unique() -> None:
    codes = [error_type.code for error_type in ERROR_TYPES]

    assert len(codes) == len(set(codes))


def test_payload_carries_the_retry_hint() -> None:
    payload = RateLimitExceededError("slow down", retry_after=2.5).to_payload()

    assert payload.code is ErrorCode.RATE_LIMITED
    assert payload.retry_after_seconds == 2.5


def test_rate_limit_error_maps_to_429() -> None:
    assert RateLimitExceededError.http_status == HTTP_TOO_MANY_REQUESTS


def test_missing_conversation_maps_to_404() -> None:
    assert ConversationNotFoundError.http_status == HTTP_NOT_FOUND


@pytest.mark.parametrize("error_type", ERROR_TYPES)
def test_payload_round_trips_back_to_the_same_error(error_type) -> None:
    original = error_type("something went wrong", retry_after=1.0)

    restored = error_from_payload(original.to_payload())

    assert type(restored) is error_type
    assert restored.message == "something went wrong"
    assert restored.retry_after == 1.0


def test_unknown_code_falls_back_to_an_internal_error() -> None:
    payload = ChatErrorPayload(code=ErrorCode.INTERNAL, message="boom")

    restored = error_from_payload(payload)

    assert isinstance(restored, ChatServiceError)
    assert restored.code is ErrorCode.INTERNAL


def test_database_error_is_a_chat_service_error() -> None:
    assert issubclass(DatabaseUnavailableError, ChatServiceError)
