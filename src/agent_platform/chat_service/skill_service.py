"""The skill-based chat service.

Builds one pydantic-ai agent per run over two toolsets: a `SkillsToolset` of
SKILL.md playbooks that tell the model how to approach a grocery question, and
a `FunctionToolset` of read-only SQL tools that actually answer it.

Streaming uses `run_stream_events` rather than `run_stream`. `run_stream` stops
at the first output matching the output type and never executes tool calls the
model makes afterwards, which would silently truncate multi-step SQL reasoning.
`run_stream_events` runs to completion and yields the full event sequence.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path

import pydantic_ai
from pydantic_ai import (
    AgentRunResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    TextPartDelta,
)
from pydantic_ai.capabilities import ProcessHistory
from pydantic_ai.exceptions import (
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
    UserError,
)
from pydantic_ai.models import Model
from pydantic_ai_skills import SkillsToolset

from src.agent_platform.chat_service.context import build_history_processor
from src.agent_platform.chat_service.conversations import ConversationStore
from src.agent_platform.chat_service.models import (
    AgentConfig,
    AgentRequest,
    AgentStatus,
    ChatInput,
    HistoryBudget,
    UsageBudget,
)
from src.agent_platform.chat_service.service import ChatService
from src.agent_platform.chat_service.streaming import (
    ErrorEvent,
    StreamEvent,
    StreamingState,
)
from src.agent_platform.errors import (
    ChatServiceError,
    InternalChatServiceError,
    ModelUnavailableError,
    RunCancelledError,
    SkillLoadError,
    UsageLimitError,
)
from src.agent_platform.grocery.deps import AgentDeps
from src.agent_platform.grocery.grocery_toolset import build_grocery_toolset
from src.agent_platform.instruction import AGENT_INSTRUCTIONS
from src.agent_platform.rate_limit import RateLimiter

LOGGER = logging.getLogger(__name__)

SCRIPT_EXECUTION_TOOL = "run_skill_script"
TOOL_RETRIES = 2
OUTPUT_RETRIES = 1

MODEL_ERROR_MESSAGE = "The model provider could not complete the request."
MODEL_CONFIG_ERROR_MESSAGE = (
    "The agent model is misconfigured. Check AGENT_MODEL and the matching "
    "provider API key."
)
MODEL_GAVE_UP_MESSAGE = (
    "The model could not complete the request within its retry budget."
)
SKILLS_MISSING_MESSAGE = "The skills directory {path} does not exist."
UNEXPECTED_ERROR_MESSAGE = "The chat service failed to complete the request."
CANCELLED_MESSAGE = "The run was cancelled before it completed."
UNEXPECTED_ERROR_LOG = "Unhandled error during run %s"


class SkillService(ChatService):
    """Chat service backed by skills plus read-only grocery SQL tools."""

    def __init__(
        self,
        conversations: ConversationStore,
        rate_limiter: RateLimiter,
        deps: AgentDeps,
        agent_config: AgentConfig,
        usage_budget: UsageBudget,
        history_budget: HistoryBudget,
        skills_directory: Path,
        model: Model | str | None = None,
    ) -> None:
        """Build the service.

        `model` overrides `agent_config.model`. It takes a constructed `Model`
        rather than a name, which is how tests substitute `TestModel` and how
        a caller can supply something a name cannot express, such as a
        `FallbackModel`.
        """

        super().__init__(conversations, rate_limiter)
        self._deps = deps
        self._agent_config = agent_config
        self._model: Model | str = model or agent_config.model
        self._usage_budget = usage_budget
        self._history_budget = history_budget
        self._skills_toolset = self._build_skills_toolset(skills_directory)
        self._grocery_toolset = build_grocery_toolset()

    @property
    def skills_toolset(self) -> SkillsToolset:
        """The loaded skills, exposed so the API can list them."""

        return self._skills_toolset

    @staticmethod
    def _build_skills_toolset(skills_directory: Path) -> SkillsToolset:
        """Load the SKILL.md playbooks from disk.

        `run_skill_script` is excluded so the agent cannot execute scripts
        found in a skill directory; the skills here are documentation, and the
        only executable surface is the SQL toolset.
        """

        if not skills_directory.is_dir():
            raise SkillLoadError(SKILLS_MISSING_MESSAGE.format(path=skills_directory))
        try:
            return SkillsToolset(
                directories=[skills_directory],
                exclude_tools=[SCRIPT_EXECUTION_TOOL],
                # SkillsToolset carries its own retry budget, which takes
                # precedence over the agent's, so both are set to the same
                # value. Its tools retry on a misspelled skill name, which is
                # exactly the mistake worth giving the model a second try at.
                max_retries=TOOL_RETRIES,
            )
        except (OSError, ValueError) as error:
            raise SkillLoadError(str(error)) from error

    def _create_agent(self, streaming_state: StreamingState) -> pydantic_ai.Agent:
        """Create the agent for one run.

        The agent is built per run because the history processor writes into
        that run's `StreamingState`. Toolsets are built once in `__init__` and
        reused, so only the cheap wiring is repeated.
        """

        return pydantic_ai.Agent(
            self._model,
            deps_type=AgentDeps,
            instructions=AGENT_INSTRUCTIONS,
            toolsets=[self._skills_toolset, self._grocery_toolset],
            capabilities=[
                ProcessHistory(
                    build_history_processor(self._history_budget, streaming_state)
                )
            ],
            model_settings=self._agent_config.to_model_settings(),
            retries={"tools": TOOL_RETRIES, "output": OUTPUT_RETRIES},
        )

    async def stream(self, chat_input: ChatInput) -> AsyncIterator[StreamEvent]:
        """Stream the answer to a chat request.

        Yields status, text deltas, tool activity, usage and exactly one
        terminal event: either `CompletedEvent` or `ErrorEvent`. The stream
        always terminates cleanly, so a client never has to infer failure from
        a dropped connection.
        """

        try:
            request, _ = await self._get_input_from_request(chat_input)
        except ChatServiceError as error:
            yield self._fail_before_run(chat_input, error)
            return

        state = StreamingState(request=request, config=self._agent_config)
        yield state.transition(AgentStatus.RUNNING)

        try:
            async for event in self._run(request, state):
                yield event
        except ChatServiceError as error:
            yield state.fail(error, AgentStatus.ABORTED)
        except (GeneratorExit, KeyboardInterrupt):
            raise
        except BaseException as error:  # noqa: BLE001 - always close the stream
            yield self._handle_unexpected(state, error)

    async def _run(
        self, request: AgentRequest, state: StreamingState
    ) -> AsyncIterator[StreamEvent]:
        """Run the agent and map its events onto the service's wire format."""

        agent = self._create_agent(state)
        history = await self._conversations.history(request.conversation_id)

        async with agent.run_stream_events(
            request.message,
            deps=self._deps,
            message_history=history,
            usage_limits=self._usage_budget.to_usage_limits(),
        ) as events:
            async for event in events:
                mapped = self._map_event(event, state)
                if mapped is not None:
                    yield mapped

            result = events.result

        if result is None:
            raise RunCancelledError(CANCELLED_MESSAGE)

        await self._conversations.append_messages(
            request.conversation_id, list(result.new_messages())
        )
        yield state.record_usage(result.usage)
        state.transition(AgentStatus.COMPLETED)
        yield state.complete()

    def _map_event(self, event: object, state: StreamingState) -> StreamEvent | None:
        """Translate one pydantic-ai event, or None if it carries no signal.

        Recording happens on `state` as a side effect, so the accumulated text
        and tool calls stay in step with what the client received.
        """

        match event:
            case PartDeltaEvent(delta=TextPartDelta(content_delta=delta)) if delta:
                return state.append_text(delta)
            case FunctionToolCallEvent(part=part):
                return state.record_tool_call(
                    tool_call_id=part.tool_call_id,
                    tool_name=part.tool_name,
                    arguments=part.args_as_json_str(),
                )
            case FunctionToolResultEvent(part=part):
                return state.record_tool_result(
                    tool_call_id=part.tool_call_id,
                    tool_name=part.tool_name or "",
                    result=str(part.content),
                )
            case AgentRunResultEvent():
                return None
            case _:
                return None

    def _fail_before_run(
        self, chat_input: ChatInput, error: ChatServiceError
    ) -> ErrorEvent:
        """Build the terminal event for a request rejected before the run.

        Rate limiting and an unknown conversation both land here. The client
        already knows the conversation id it sent, so the event only has to
        carry the reason.
        """

        state = StreamingState(
            request=AgentRequest(
                query_id=self._generate_query_id(),
                conversation_id=chat_input.conversation_id or "",
                message=chat_input.message,
                is_new_conversation=chat_input.conversation_id is None,
            ),
            config=self._agent_config,
        )
        return state.fail(error, AgentStatus.ABORTED)

    def _handle_unexpected(
        self, state: StreamingState, error: BaseException
    ) -> ErrorEvent:
        """Map a non-`ChatServiceError` failure onto a terminal error event."""

        if isinstance(error, asyncio.CancelledError):
            return state.fail(
                RunCancelledError(CANCELLED_MESSAGE), AgentStatus.CANCELLED
            )
        if isinstance(error, UsageLimitExceeded):
            return state.fail(UsageLimitError(str(error)), AgentStatus.ABORTED)
        if isinstance(error, ModelHTTPError):
            LOGGER.warning(UNEXPECTED_ERROR_LOG, state.request.query_id, exc_info=error)
            return state.fail(
                ModelUnavailableError(MODEL_ERROR_MESSAGE), AgentStatus.ABORTED
            )
        if isinstance(error, UserError):
            return state.fail(
                ModelUnavailableError(MODEL_CONFIG_ERROR_MESSAGE), AgentStatus.ABORTED
            )
        if isinstance(error, UnexpectedModelBehavior):
            LOGGER.warning(UNEXPECTED_ERROR_LOG, state.request.query_id, exc_info=error)
            return state.fail(
                ModelUnavailableError(MODEL_GAVE_UP_MESSAGE), AgentStatus.ABORTED
            )
        LOGGER.exception(UNEXPECTED_ERROR_LOG, state.request.query_id, exc_info=error)
        return state.fail(
            InternalChatServiceError(UNEXPECTED_ERROR_MESSAGE), AgentStatus.ABORTED
        )
