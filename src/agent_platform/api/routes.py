"""HTTP routes for the chat service.

`/chat/stream` is the primary route. `/chat` drains the same generator, so the
two cannot diverge in behavior.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import pydantic
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from pydantic_ai.messages import ModelMessagesTypeAdapter
from sse_starlette.sse import EventSourceResponse

from src.agent_platform.api.ui import CHAT_UI_HTML
from src.agent_platform.chat_service.models import ChatInput, ChatOutput
from src.agent_platform.chat_service.streaming import StreamEvent

LOGGER = logging.getLogger(__name__)

DOCS_PATH = "/docs"
ROOT_PATH = "/"
UI_PATH = "/ui"
FAVICON_PATH = "/favicon.ico"
HEALTH_PATH = "/health"
SKILLS_PATH = "/skills"
CHAT_PATH = "/chat"
CHAT_STREAM_PATH = "/chat/stream"
CONVERSATION_CONTEXT_PATH = "/conversations/{conversation_id}/context"

HEALTHY_STATUS = "ok"
CLIENT_DISCONNECTED_LOG = "Client disconnected from stream for conversation %s"


class HealthResponse(pydantic.BaseModel):
    """Liveness plus the resolved model, which is the usual misconfiguration."""

    status: str
    model: str
    skills: list[str]


class SkillSummary(pydantic.BaseModel):
    """One loaded skill, as advertised to the model."""

    name: str
    description: str
    resources: list[str]


class ConversationContext(pydantic.BaseModel):
    """The stored history of a conversation, exactly as the model would see it.

    `messages` is the pydantic-ai serialization of `list[ModelMessage]`, so
    what this returns is what a subsequent turn would replay, not a summary
    of it.
    """

    conversation_id: str
    message_count: int
    messages: list[dict]


def build_router() -> APIRouter:
    """Build the chat service routes."""

    router = APIRouter()

    @router.get(ROOT_PATH, response_class=HTMLResponse, include_in_schema=False)
    @router.get(UI_PATH, response_class=HTMLResponse, include_in_schema=False)
    async def chat_ui() -> HTMLResponse:
        """Serve the interactive single-page chat UI."""

        return HTMLResponse(content=CHAT_UI_HTML)

    @router.get(FAVICON_PATH, include_in_schema=False)
    async def favicon() -> Response:
        """Return 204 No Content for browser favicon requests."""

        return Response(status_code=204)

    @router.get(HEALTH_PATH, response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        """Report that the service is up, and what it is configured with."""

        state = request.app.state.platform
        return HealthResponse(
            status=HEALTHY_STATUS,
            model=state.config.agent.model,
            skills=sorted(state.service.skills_toolset.skills),
        )

    @router.get(SKILLS_PATH, response_model=list[SkillSummary])
    async def list_skills(request: Request) -> list[SkillSummary]:
        """List the skill playbooks the agent can load."""

        state = request.app.state.platform
        skills = state.service.skills_toolset.skills
        return [
            SkillSummary(
                name=skills[name].name,
                description=skills[name].description,
                resources=[resource.name for resource in skills[name].resources],
            )
            for name in sorted(skills)
        ]

    @router.post(CHAT_PATH, response_model=ChatOutput)
    async def chat(request: Request, chat_input: ChatInput) -> ChatOutput:
        """Answer a question and return the complete result."""

        return await request.app.state.platform.service.respond(chat_input)

    @router.post(CHAT_STREAM_PATH)
    async def chat_stream(
        request: Request, chat_input: ChatInput
    ) -> EventSourceResponse:
        """Answer a question, streaming events as they happen.

        Each SSE message carries the event type in the `event` field and the
        event's JSON in `data`, so a client can dispatch without parsing the
        body first.
        """

        service = request.app.state.platform.service

        async def event_source() -> AsyncIterator[dict[str, str]]:
            async for event in service.stream(chat_input):
                if await request.is_disconnected():
                    LOGGER.info(CLIENT_DISCONNECTED_LOG, chat_input.conversation_id)
                    break
                yield _to_sse(event)

        return EventSourceResponse(event_source())

    @router.get(CONVERSATION_CONTEXT_PATH, response_model=ConversationContext)
    async def conversation_context(
        request: Request, conversation_id: str
    ) -> ConversationContext:
        """Return exactly what a next turn would send to the model.

        Raises:
            ConversationNotFoundError: If the conversation is unknown.
        """

        store = request.app.state.platform.conversations
        messages = await store.history(conversation_id)
        return ConversationContext(
            conversation_id=conversation_id,
            message_count=len(messages),
            messages=ModelMessagesTypeAdapter.dump_python(messages, mode="json"),
        )

    return router


def _to_sse(event: StreamEvent) -> dict[str, str]:
    """Render one stream event as an SSE message."""

    return {"event": event.type.value, "data": event.model_dump_json()}
