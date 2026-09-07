"""Base chat service: turns a transport request into an agent request.

`ChatService` owns everything that is independent of how the answer is
produced, so a subclass only has to implement the run itself. It resolves the
conversation, applies the rate limit and generates the query id.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from src.agent_platform.chat_service.conversations import (
    ConversationStore,
    derive_title,
)
from src.agent_platform.chat_service.models import (
    AgentRequest,
    AgentStatus,
    ChatInput,
    ChatOutput,
    Conversation,
)
from src.agent_platform.chat_service.streaming import (
    CompletedEvent,
    ErrorEvent,
    StatusEvent,
    StreamEvent,
    ToolCallEvent,
)
from src.agent_platform.errors import error_from_payload
from src.agent_platform.rate_limit import RateLimiter


class ChatService:
    """Shared request handling for every chat service variant."""

    def __init__(
        self,
        conversations: ConversationStore,
        rate_limiter: RateLimiter,
    ) -> None:
        self._conversations = conversations
        self._rate_limiter = rate_limiter

    async def stream(self, chat_input: ChatInput) -> AsyncIterator[StreamEvent]:
        """Stream the answer to a chat request.

        Raises:
            NotImplementedError: Subclasses provide the run.
        """

        raise NotImplementedError
        yield  # pragma: no cover - marks this as an async generator

    async def respond(self, chat_input: ChatInput) -> ChatOutput:
        """Collect a full answer by draining `stream`.

        The non-streaming path is the streaming path drained to completion, so
        both routes go through identical logic and cannot drift apart.

        Raises:
            ChatServiceError: If the run reported a terminal failure.
        """

        query_id = ""
        conversation_id = chat_input.conversation_id or ""
        text = ""
        status = AgentStatus.PENDING
        tool_names: list[str] = []

        async for event in self.stream(chat_input):
            if isinstance(event, StatusEvent):
                status = event.status
            elif isinstance(event, ToolCallEvent):
                tool_names.append(event.tool_name)
            elif isinstance(event, CompletedEvent):
                query_id = event.query_id
                conversation_id = event.conversation_id
                text = event.text
                status = AgentStatus.COMPLETED
            elif isinstance(event, ErrorEvent):
                raise error_from_payload(event.error)

        return ChatOutput(
            query_id=query_id,
            conversation_id=conversation_id,
            status=status,
            text=text,
            tool_calls=tool_names,
        )

    async def _get_input_from_request(
        self, chat_input: ChatInput
    ) -> tuple[AgentRequest, Conversation]:
        """Resolve a chat request against its conversation.

        A new conversation is created when no id is supplied, and titled from
        the first message. An existing id is looked up, which raises if it is
        unknown rather than silently starting a new thread.

        Args:
            chat_input: The validated request from the transport layer.

        Returns:
            The agent request and the conversation it belongs to.
        """

        is_new_conversation = chat_input.conversation_id is None
        if is_new_conversation:
            conversation = await self._create_conversation(chat_input)
        else:
            conversation = await self._conversations.get(chat_input.conversation_id)

        await self._rate_limiter.acquire(conversation.id)

        return AgentRequest(
            query_id=self._generate_query_id(),
            conversation_id=conversation.id,
            message=chat_input.message,
            context=dict(chat_input.context),
            metadata=dict(chat_input.metadata),
            is_new_conversation=is_new_conversation,
        ), conversation

    async def _create_conversation(self, chat_input: ChatInput) -> Conversation:
        """Create a conversation titled from the request's first message."""

        return await self._conversations.create(title=derive_title(chat_input.message))

    def _generate_query_id(self) -> str:
        """Return a fresh identifier for a single question."""

        return str(uuid.uuid4())
