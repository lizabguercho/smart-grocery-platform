"""FastAPI application factory.

The database pool and the toolsets are built once in the lifespan and shared by
every request. Building them per request would reconnect to a remote Supabase
database on every question, and would reload the skills from disk each time.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic_ai.models import Model

from src.agent_platform.api.routes import build_router
from src.agent_platform.chat_service.conversations import (
    ConversationStore,
    InMemoryConversationStore,
)
from src.agent_platform.chat_service.skill_service import SkillService
from src.agent_platform.config import AgentPlatformConfig
from src.agent_platform.errors import ChatServiceError
from src.agent_platform.grocery.database import AsyncGroceryDatabase
from src.agent_platform.grocery.deps import AgentDeps
from src.agent_platform.rate_limit import RateLimiter

LOGGER = logging.getLogger(__name__)

API_TITLE = "Smart Grocery Platform chat service"
API_DESCRIPTION = (
    "Ask questions about grocery prices across Shufersal, Rami Levy and "
    "Victory. Answers come from skills plus read-only SQL over the shared "
    "analytical database."
)
API_VERSION = "0.1.0"
RETRY_AFTER_HEADER = "Retry-After"


@dataclass
class AppState:
    """Long-lived objects shared by every request."""

    config: AgentPlatformConfig
    database: AsyncGroceryDatabase
    service: SkillService
    conversations: ConversationStore


def create_app(
    config: AgentPlatformConfig | None = None,
    conversations: ConversationStore | None = None,
    model: Model | str | None = None,
) -> FastAPI:
    """Build the chat service application.

    Args:
        config: Platform configuration. Read from the environment if omitted.
        conversations: Conversation store. In-memory if omitted.
        model: Overrides the configured model, which is how tests avoid
            needing a provider API key.
    """

    resolved_config = config or AgentPlatformConfig.from_env()
    store = conversations or InMemoryConversationStore()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = AsyncGroceryDatabase(resolved_config.database)
        await database.open()
        service = SkillService(
            conversations=store,
            rate_limiter=RateLimiter(resolved_config.rate_limit),
            deps=AgentDeps(database=database),
            agent_config=resolved_config.agent,
            usage_budget=resolved_config.usage,
            history_budget=resolved_config.history,
            skills_directory=resolved_config.skills_directory,
            model=model,
        )
        app.state.platform = AppState(
            config=resolved_config,
            database=database,
            service=service,
            conversations=store,
        )
        server_url = f"http://{resolved_config.host}:{resolved_config.port}"
        logging.getLogger("uvicorn.error").info(
            "Chat service endpoints ready:\n"
            "  • Web Chat UI:                   %s/\n"
            "  • Interactive Docs (Swagger UI): %s/docs\n"
            "  • Health check:                  %s/health\n"
            "  • Available skills:              %s/skills\n"
            "  • Chat stream (SSE):             POST %s/chat/stream\n"
            "  • Chat completion:               POST %s/chat",
            server_url,
            server_url,
            server_url,
            server_url,
            server_url,
            server_url,
        )
        try:
            yield
        finally:
            await database.close()

    app = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=API_VERSION,
        lifespan=lifespan,
    )
    app.include_router(build_router())

    @app.exception_handler(ChatServiceError)
    async def handle_chat_service_error(
        request: Request, error: ChatServiceError
    ) -> JSONResponse:
        """Render any service error through its own status and payload."""

        headers = {}
        if error.retry_after is not None:
            headers[RETRY_AFTER_HEADER] = str(int(error.retry_after) + 1)
        return JSONResponse(
            status_code=error.http_status,
            content=error.to_payload().model_dump(mode="json"),
            headers=headers,
        )

    return app
