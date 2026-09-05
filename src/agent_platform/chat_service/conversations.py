"""Storage for chat threads and their model messages.

The service depends on the `ConversationStore` protocol, not on the in-memory
implementation, so a Postgres-backed store can replace it without touching the
service. History is kept as `ModelMessage` objects rather than plain text: that
is the form pydantic-ai replays, so nothing is lost or re-derived between turns.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Protocol

from pydantic_ai.messages import ModelMessage

from src.agent_platform.chat_service.models import Conversation
from src.agent_platform.errors import ConversationNotFoundError

UNKNOWN_CONVERSATION_MESSAGE = "Conversation {conversation_id} does not exist."
TITLE_MAX_LENGTH = 60
TITLE_ELLIPSIS = "..."


def derive_title(message: str) -> str:
    """Build a short conversation title from its first message."""

    collapsed = " ".join(message.split())
    if len(collapsed) <= TITLE_MAX_LENGTH:
        return collapsed
    return collapsed[: TITLE_MAX_LENGTH - len(TITLE_ELLIPSIS)] + TITLE_ELLIPSIS


class ConversationStore(Protocol):
    """Persistence boundary for chat threads."""

    async def create(self, title: str | None = None) -> Conversation:
        """Create a new conversation with a generated id."""
        ...

    async def get(self, conversation_id: str) -> Conversation:
        """Return an existing conversation.

        Raises:
            ConversationNotFoundError: If the id is unknown.
        """
        ...

    async def history(self, conversation_id: str) -> list[ModelMessage]:
        """Return the recorded messages for a conversation, oldest first."""
        ...

    async def append_messages(
        self, conversation_id: str, messages: list[ModelMessage]
    ) -> None:
        """Append newly produced messages to a conversation."""
        ...


class InMemoryConversationStore:
    """Process-local `ConversationStore`, sufficient for running locally.

    Access is guarded by a lock because a single service instance streams
    several runs concurrently.
    """

    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._messages: dict[str, list[ModelMessage]] = {}
        self._lock = asyncio.Lock()

    async def create(self, title: str | None = None) -> Conversation:
        """Create a new conversation with a generated id."""

        conversation = Conversation(
            id=str(uuid.uuid4()),
            created_at=datetime.now(UTC),
            title=title,
        )
        async with self._lock:
            self._conversations[conversation.id] = conversation
            self._messages[conversation.id] = []
        return conversation

    async def get(self, conversation_id: str) -> Conversation:
        """Return an existing conversation.

        Raises:
            ConversationNotFoundError: If the id is unknown.
        """

        async with self._lock:
            conversation = self._conversations.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(
                UNKNOWN_CONVERSATION_MESSAGE.format(conversation_id=conversation_id)
            )
        return conversation

    async def history(self, conversation_id: str) -> list[ModelMessage]:
        """Return a copy of the recorded messages, oldest first."""

        await self.get(conversation_id)
        async with self._lock:
            return list(self._messages[conversation_id])

    async def append_messages(
        self, conversation_id: str, messages: list[ModelMessage]
    ) -> None:
        """Append newly produced messages to a conversation."""

        await self.get(conversation_id)
        async with self._lock:
            self._messages[conversation_id].extend(messages)
