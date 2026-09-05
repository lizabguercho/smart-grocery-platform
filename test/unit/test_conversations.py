"""Tests for conversation storage."""

from __future__ import annotations

import pytest
from pydantic_ai.messages import ModelRequest, UserPromptPart

from src.agent_platform.chat_service.conversations import (
    TITLE_MAX_LENGTH,
    InMemoryConversationStore,
    derive_title,
)
from src.agent_platform.errors import ConversationNotFoundError


@pytest.fixture
def store() -> InMemoryConversationStore:
    return InMemoryConversationStore()


def message(text: str) -> ModelRequest:
    return ModelRequest(parts=[UserPromptPart(content=text)])


@pytest.mark.anyio
async def test_create_assigns_an_id_and_timestamp(store) -> None:
    conversation = await store.create(title="Milk prices")

    assert conversation.id
    assert conversation.title == "Milk prices"
    assert conversation.created_at is not None


@pytest.mark.anyio
async def test_conversations_get_distinct_ids(store) -> None:
    first = await store.create()
    second = await store.create()

    assert first.id != second.id


@pytest.mark.anyio
async def test_get_returns_a_created_conversation(store) -> None:
    created = await store.create()

    assert (await store.get(created.id)).id == created.id


@pytest.mark.anyio
async def test_get_rejects_an_unknown_id(store) -> None:
    with pytest.raises(ConversationNotFoundError):
        await store.get("missing")


@pytest.mark.anyio
async def test_history_starts_empty(store) -> None:
    conversation = await store.create()

    assert await store.history(conversation.id) == []


@pytest.mark.anyio
async def test_appended_messages_are_returned_in_order(store) -> None:
    conversation = await store.create()

    await store.append_messages(conversation.id, [message("first")])
    await store.append_messages(conversation.id, [message("second")])

    history = await store.history(conversation.id)
    assert len(history) == 2
    assert history[0].parts[0].content == "first"


@pytest.mark.anyio
async def test_history_returns_a_copy(store) -> None:
    conversation = await store.create()
    await store.append_messages(conversation.id, [message("first")])

    history = await store.history(conversation.id)
    history.append(message("mutation"))

    # A caller mutating the returned list must not corrupt stored history.
    assert len(await store.history(conversation.id)) == 1


@pytest.mark.anyio
async def test_appending_to_an_unknown_conversation_is_rejected(store) -> None:
    with pytest.raises(ConversationNotFoundError):
        await store.append_messages("missing", [message("first")])


@pytest.mark.anyio
async def test_conversations_do_not_share_history(store) -> None:
    first = await store.create()
    second = await store.create()

    await store.append_messages(first.id, [message("first")])

    assert await store.history(second.id) == []


def test_short_titles_are_kept_whole() -> None:
    assert derive_title("Where is milk cheapest?") == "Where is milk cheapest?"


def test_titles_collapse_whitespace() -> None:
    assert derive_title("Where   is\nmilk?") == "Where is milk?"


def test_long_titles_are_truncated() -> None:
    title = derive_title("x" * 500)

    assert len(title) == TITLE_MAX_LENGTH
    assert title.endswith("...")
