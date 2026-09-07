"""Tests for the HTTP routes.

The app is built with a fake database and `TestModel`, so the routes are
exercised without a live database or a provider API key.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.models.test import TestModel

from src.agent_platform.api.app import create_app
from src.agent_platform.chat_service.models import (
    AgentConfig,
    HistoryBudget,
    RateLimitPolicy,
    UsageBudget,
)
from src.agent_platform.config import (
    AgentPlatformConfig,
    RemoteDatabaseSettings,
    default_skills_directory,
)
from src.agent_platform.errors import ErrorCode
from test.unit.conftest import FakeGroceryDatabase

CHEAPEST_SUMMARY = "counted"
ANSWER = "Rami Levy wins most often."
SUMMARY_ROW = (100, 20, 50, 10, 25, 60, 15, 20)
MODEL_NAME = "openai:gpt-5.2"


def make_config(burst: int = 100) -> AgentPlatformConfig:
    return AgentPlatformConfig(
        agent=AgentConfig(model=MODEL_NAME, temperature=0.0, max_tokens=256, top_p=1.0),
        usage=UsageBudget(
            request_limit=5, tool_calls_limit=5, total_tokens_limit=10_000
        ),
        rate_limit=RateLimitPolicy(requests_per_minute=600, burst=burst),
        history=HistoryBudget(max_messages=50, max_characters=50_000),
        database=RemoteDatabaseSettings(
            host="db.example",
            port=5432,
            dbname="postgres",
            user="contributor",
            password="secret",
            statement_timeout_ms=1000,
        ),
        skills_directory=default_skills_directory(),
    )


@pytest.fixture
def client():
    """A client whose app talks to a fake database and a fake model."""

    database = FakeGroceryDatabase(rows={CHEAPEST_SUMMARY: [SUMMARY_ROW]})
    app = create_app(
        config=make_config(),
        model=TestModel(
            call_tools=["cheapest_chain_summary"], custom_output_text=ANSWER
        ),
    )
    with (
        patch("src.agent_platform.api.app.AsyncGroceryDatabase", return_value=database),
        TestClient(app) as test_client,
    ):
        yield test_client


def sse_events(body: str) -> list[tuple[str, dict]]:
    """Parse an SSE response body into (event name, payload) pairs."""

    events: list[tuple[str, dict]] = []
    name = ""
    for line in body.splitlines():
        if line.startswith("event:"):
            name = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            events.append((name, json.loads(line.removeprefix("data:").strip())))
    return events


def test_root_serves_chat_ui(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Smart Grocery Platform" in response.text
    assert 'id="messages-container"' in response.text


def test_ui_alias_serves_chat_ui(client) -> None:
    response = client.get("/ui")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Smart Grocery Platform" in response.text


def test_favicon_returns_no_content(client) -> None:
    response = client.get("/favicon.ico")

    assert response.status_code == 204


def test_health_reports_the_model_and_skills(client) -> None:
    body = client.get("/health").json()

    assert body["status"] == "ok"
    assert body["model"] == MODEL_NAME
    assert "grocery-database" in body["skills"]


def test_skills_route_lists_the_playbooks(client) -> None:
    body = client.get("/skills").json()

    names = {skill["name"] for skill in body}
    assert names == {"grocery-database", "price-comparison", "chain-competitiveness"}
    reference = next(s for s in body if s["name"] == "grocery-database")
    assert reference["resources"] == ["REFERENCE.md"]


def test_chat_returns_the_full_answer(client) -> None:
    body = client.post("/chat", json={"message": "which chain is cheapest?"}).json()

    assert body["text"] == ANSWER
    assert body["status"] == "completed"
    assert body["conversation_id"]


def test_chat_stream_is_server_sent_events(client) -> None:
    response = client.post("/chat/stream", json={"message": "hi"})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_chat_stream_emits_the_expected_event_sequence(client) -> None:
    response = client.post("/chat/stream", json={"message": "hi"})

    names = [name for name, _ in sse_events(response.text)]
    assert names[0] == "status"
    assert names[-1] == "completed"
    assert "tool_call" in names
    assert "tool_result" in names
    assert "text_delta" in names


def test_streamed_deltas_rebuild_the_answer(client) -> None:
    response = client.post("/chat/stream", json={"message": "hi"})

    deltas = [
        payload["delta"]
        for name, payload in sse_events(response.text)
        if name == "text_delta"
    ]
    assert "".join(deltas) == ANSWER


def test_conversation_context_returns_the_stored_messages(client) -> None:
    created = client.post("/chat", json={"message": "hi"}).json()

    body = client.get(f"/conversations/{created['conversation_id']}/context").json()

    assert body["conversation_id"] == created["conversation_id"]
    assert body["message_count"] == len(body["messages"])
    assert body["message_count"] > 0


def test_conversation_context_rejects_an_unknown_id(client) -> None:
    response = client.get("/conversations/missing/context")

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.CONVERSATION_NOT_FOUND.value


def test_an_empty_message_is_rejected_by_validation(client) -> None:
    assert client.post("/chat", json={"message": ""}).status_code == 422


def test_an_unknown_field_is_rejected_by_validation(client) -> None:
    response = client.post("/chat", json={"message": "hi", "surprise": 1})

    assert response.status_code == 422


def test_continuing_an_unknown_conversation_fails_on_the_chat_route(client) -> None:
    response = client.post(
        "/chat", json={"message": "hi", "conversation_id": "missing"}
    )

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.CONVERSATION_NOT_FOUND.value


def test_rate_limiting_returns_429_with_a_retry_after_header() -> None:
    database = FakeGroceryDatabase(rows={CHEAPEST_SUMMARY: [SUMMARY_ROW]})
    app = create_app(
        config=make_config(burst=1),
        model=TestModel(
            call_tools=["cheapest_chain_summary"], custom_output_text=ANSWER
        ),
    )
    with (
        patch("src.agent_platform.api.app.AsyncGroceryDatabase", return_value=database),
        TestClient(app) as client,
    ):
        created = client.post("/chat", json={"message": "hi"}).json()

        response = client.post(
            "/chat",
            json={
                "message": "again",
                "conversation_id": created["conversation_id"],
            },
        )

    assert response.status_code == 429
    assert response.json()["code"] == ErrorCode.RATE_LIMITED.value
    assert "Retry-After" in response.headers


def test_openapi_schema_is_generated(client) -> None:
    """FastAPI's schema is the reason the extra dependency is worth it."""

    schema = client.get("/openapi.json").json()

    assert "/chat/stream" in schema["paths"]
    assert "/chat" in schema["paths"]
