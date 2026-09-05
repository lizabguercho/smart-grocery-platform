"""Tests for the streaming skill service.

`TestModel` stands in for a provider, so these tests need no API key and no
network. The fake database answers the one tool the model is allowed to call.
"""

from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from src.agent_platform.chat_service.conversations import InMemoryConversationStore
from src.agent_platform.chat_service.models import (
    AgentConfig,
    AgentStatus,
    ChatInput,
    HistoryBudget,
    RateLimitPolicy,
    UsageBudget,
)
from src.agent_platform.chat_service.skill_service import SkillService
from src.agent_platform.chat_service.streaming import (
    CompletedEvent,
    ErrorEvent,
    StatusEvent,
    TextDeltaEvent,
    ToolCallEvent,
    ToolResultEvent,
    UsageEvent,
)
from src.agent_platform.config import default_skills_directory
from src.agent_platform.errors import ErrorCode, RateLimitExceededError
from src.agent_platform.grocery.deps import AgentDeps
from src.agent_platform.rate_limit import RateLimiter
from test.unit.conftest import FakeGroceryDatabase

CHEAPEST_SUMMARY = "counted"
ANSWER = "Rami Levy wins most often."
SUMMARY_ROW = (100, 20, 50, 10, 25, 60, 15, 20)


@pytest.fixture
def database() -> FakeGroceryDatabase:
    return FakeGroceryDatabase(rows={CHEAPEST_SUMMARY: [SUMMARY_ROW]})


def make_service(
    database: FakeGroceryDatabase,
    conversations: InMemoryConversationStore | None = None,
    rate_limiter: RateLimiter | None = None,
    model: TestModel | None = None,
) -> SkillService:
    return SkillService(
        conversations=conversations or InMemoryConversationStore(),
        rate_limiter=rate_limiter
        or RateLimiter(RateLimitPolicy(requests_per_minute=600, burst=100)),
        deps=AgentDeps(database=database),
        agent_config=AgentConfig(
            model="openai:gpt-5.2", temperature=0.0, max_tokens=256, top_p=1.0
        ),
        usage_budget=UsageBudget(
            request_limit=5, tool_calls_limit=5, total_tokens_limit=10_000
        ),
        history_budget=HistoryBudget(max_messages=50, max_characters=50_000),
        skills_directory=default_skills_directory(),
        model=model
        or TestModel(call_tools=["cheapest_chain_summary"], custom_output_text=ANSWER),
    )


async def collect(service: SkillService, chat_input: ChatInput) -> list:
    return [event async for event in service.stream(chat_input)]


@pytest.mark.anyio
async def test_stream_starts_with_a_running_status(database) -> None:
    events = await collect(make_service(database), ChatInput(message="hi"))

    assert isinstance(events[0], StatusEvent)
    assert events[0].status is AgentStatus.RUNNING


@pytest.mark.anyio
async def test_the_first_event_reveals_the_conversation_id(database) -> None:
    events = await collect(make_service(database), ChatInput(message="hi"))

    # A client must learn the conversation id immediately, so it can continue
    # the thread even if the run later fails.
    assert events[0].conversation_id
    assert events[0].query_id


@pytest.mark.anyio
async def test_stream_ends_with_the_completed_answer(database) -> None:
    events = await collect(make_service(database), ChatInput(message="hi"))

    assert isinstance(events[-1], CompletedEvent)
    assert events[-1].text == ANSWER


@pytest.mark.anyio
async def test_text_arrives_as_deltas_that_rebuild_the_answer(database) -> None:
    events = await collect(make_service(database), ChatInput(message="hi"))

    deltas = [event.delta for event in events if isinstance(event, TextDeltaEvent)]
    assert len(deltas) > 1
    assert "".join(deltas) == ANSWER


@pytest.mark.anyio
async def test_tool_calls_and_results_are_streamed(database) -> None:
    events = await collect(make_service(database), ChatInput(message="hi"))

    calls = [event for event in events if isinstance(event, ToolCallEvent)]
    results = [event for event in events if isinstance(event, ToolResultEvent)]
    assert [call.tool_name for call in calls] == ["cheapest_chain_summary"]
    assert len(results) == 1
    assert calls[0].tool_call_id == results[0].tool_call_id


@pytest.mark.anyio
async def test_usage_is_reported_before_completion(database) -> None:
    events = await collect(make_service(database), ChatInput(message="hi"))

    usage = [event for event in events if isinstance(event, UsageEvent)]
    assert len(usage) == 1
    assert usage[0].requests > 0
    assert isinstance(events[-1], CompletedEvent)


@pytest.mark.anyio
async def test_the_tool_reached_the_database(database) -> None:
    await collect(make_service(database), ChatInput(message="hi"))

    assert database.params_for(CHEAPEST_SUMMARY) == (2,)


@pytest.mark.anyio
async def test_history_is_recorded_for_the_next_turn(database) -> None:
    store = InMemoryConversationStore()
    service = make_service(database, conversations=store)

    events = await collect(service, ChatInput(message="hi"))

    conversation_id = events[0].conversation_id
    assert len(await store.history(conversation_id)) > 0


@pytest.mark.anyio
async def test_a_second_turn_replays_the_first(database) -> None:
    store = InMemoryConversationStore()
    service = make_service(database, conversations=store)
    first = await collect(service, ChatInput(message="hi"))
    conversation_id = first[0].conversation_id
    before = len(await store.history(conversation_id))

    await collect(
        service, ChatInput(message="and again", conversation_id=conversation_id)
    )

    assert len(await store.history(conversation_id)) > before


@pytest.mark.anyio
async def test_every_model_request_is_audited(database) -> None:
    service = make_service(database)
    state_holder = {}
    original = service._create_agent

    def capture(state):
        state_holder["state"] = state
        return original(state)

    service._create_agent = capture

    await collect(service, ChatInput(message="hi"))

    audits = state_holder["state"].model_requests
    assert len(audits) >= 1
    assert all(audit.message_count > 0 for audit in audits)
    assert audits[0].instructions


@pytest.mark.anyio
async def test_an_unknown_conversation_ends_the_stream_with_an_error(
    database,
) -> None:
    events = await collect(
        make_service(database), ChatInput(message="hi", conversation_id="missing")
    )

    assert len(events) == 1
    assert isinstance(events[0], ErrorEvent)
    assert events[0].error.code is ErrorCode.CONVERSATION_NOT_FOUND


@pytest.mark.anyio
async def test_rate_limiting_ends_the_stream_with_an_error(database) -> None:
    store = InMemoryConversationStore()
    limiter = RateLimiter(RateLimitPolicy(requests_per_minute=60, burst=1))
    service = make_service(database, conversations=store, rate_limiter=limiter)
    first = await collect(service, ChatInput(message="hi"))
    conversation_id = first[0].conversation_id

    events = await collect(
        service, ChatInput(message="again", conversation_id=conversation_id)
    )

    assert isinstance(events[0], ErrorEvent)
    assert events[0].error.code is ErrorCode.RATE_LIMITED
    assert events[0].error.retry_after_seconds is not None


@pytest.mark.anyio
async def test_respond_returns_the_drained_stream(database) -> None:
    output = await make_service(database).respond(ChatInput(message="hi"))

    assert output.status is AgentStatus.COMPLETED
    assert output.text == ANSWER
    assert output.tool_calls == ["cheapest_chain_summary"]
    assert output.conversation_id


@pytest.mark.anyio
async def test_respond_raises_the_error_the_stream_reported(database) -> None:
    store = InMemoryConversationStore()
    limiter = RateLimiter(RateLimitPolicy(requests_per_minute=60, burst=1))
    service = make_service(database, conversations=store, rate_limiter=limiter)
    first = await service.respond(ChatInput(message="hi"))

    with pytest.raises(RateLimitExceededError):
        await service.respond(
            ChatInput(message="again", conversation_id=first.conversation_id)
        )


@pytest.mark.anyio
async def test_a_bad_tool_argument_is_retried_rather_than_crashing(
    database,
) -> None:
    """A missing product is handed back to the model as a retry.

    `TestModel` always sends the same arguments, so it cannot recover and the
    retry budget is exhausted. What matters is that the run still ends with a
    typed terminal error rather than an unhandled crash.
    """

    empty = FakeGroceryDatabase(rows={})
    service = make_service(
        empty,
        model=TestModel(
            call_tools=["compare_product_prices"], custom_output_text=ANSWER
        ),
    )

    events = await collect(service, ChatInput(message="hi"))

    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].error.code is ErrorCode.MODEL_UNAVAILABLE


def test_the_service_exposes_its_skills(database) -> None:
    assert set(make_service(database).skills_toolset.skills) == {
        "grocery-database",
        "price-comparison",
        "chain-competitiveness",
    }
