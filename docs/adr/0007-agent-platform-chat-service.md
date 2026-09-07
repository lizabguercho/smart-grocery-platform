# 0007. Agent platform chat service

Date: 2026-09-05

Status: Accepted

Related: [Documentation map](../README.md) ·
[Agent platform guide](../agent_platform.md) ·
[ADR 0003 — remote analytical database](0003-remote-analytical-database.md)

## Context

The analytical layer answers real business questions, but only through
hand-written SQL. Asking "where is this product cheapest" or "which chain wins
on dairy" required opening a SQL client and knowing the schema.

The project roadmap warns against adding infrastructure without an analytical
reason, so a chat service has to justify itself and stay small. Its value is
that it makes the existing analysis reachable in plain language, including in
Hebrew, and demonstrable in a portfolio setting, without becoming the story of
the project.

Two libraries were already added to `pyproject.toml` for this purpose:
`pydantic-ai` and `pydantic-ai-skills`.

## Decision

A `src/agent_platform` package serving a streaming chat service over the
**remote** analytical database, with the following choices.

### An agent with skills as documentation and SQL as capability

In `pydantic-ai-skills`, a skill is a `SKILL.md` markdown playbook, not
executable code. So the two concerns are separated:

- A `SkillsToolset` loads three playbooks from `src/agent_platform/skills/`.
  They explain the schema, its caveats, and the procedure for each question
  type. The model loads them on demand via `load_skill`.
- A `FunctionToolset` provides five read-only SQL tools that do the work.

Both are passed to one `Agent(toolsets=[...])`.

The alternative, putting SQL in skill scripts, was rejected: it would mean
executing files from a directory, and `run_skill_script` is explicitly excluded
for that reason.

### No free-form SQL tool

Every statement is a named constant in `grocery/queries.py` with `%s`
parameters. The agent chooses which of five statements to run and with what
arguments; it cannot compose SQL.

This bounds the blast radius to queries that were reviewed and tested, and it
means an injected instruction in a product name cannot become a query. Defence
in depth comes from the connection itself: `default_transaction_read_only=on`
and `statement_timeout` are set as server-side libpq session options, so a
write or an unbounded scan fails at the database even if the application layer
is wrong.

### Ties are computed, not read

`grocery.price_comparison.cheapest_chain` is a display label that folds ties
into strings such as `Shufersal & Rami Levy` and `All three`. It has seven
distinct values, so grouping by it produces seven buckets rather than three and
silently misstates "which chain is cheapest most often".

The tools therefore derive the cheapest chain from the price columns with
`LEAST`, which skips NULLs, and report outright wins separately from ties. The
derived counts reproduce the stored labels exactly (1,984 / 8,250 / 1,321
outright plus 3,261 tied = 14,816), which is how the SQL was validated.

### Context is controlled in one place

Conversation history is shaped by a `ProcessHistory` capability. pydantic-ai
calls it immediately before each model request and sends exactly what it
returns, so it is both the only place the outbound context is decided and the
only place it needs to be observed. Every resolved payload is recorded on
`StreamingState.model_requests`, and `GET /conversations/{id}/context` exposes
the stored history through `ModelMessagesTypeAdapter`.

Trimming operates on whole conversation turns rather than individual messages,
because a turn boundary is the only cut that cannot separate a `ToolCallPart`
from its `ToolReturnPart`. Providers reject that pairing when it is broken.

`history_processors=` was removed in pydantic-ai 2.x, so the capability API is
the current mechanism, not a preference.

### Streaming through `run_stream_events`

`agent.run_stream()` stops at the first output matching the output type and
never executes tool calls the model makes afterwards. For multi-step SQL
reasoning that would silently truncate the answer. `run_stream_events` runs to
completion and yields the full event sequence.

Provider events are mapped onto the platform's own `StreamEvent` union, so the
client contract does not move when pydantic-ai does.

### Two independent limits

Rate limiting bounds how often a run may **start**: a token bucket per
conversation, with an injected clock so tests are deterministic, mirroring the
existing SuperCompare client. `UsageLimits` bounds what a started run may
**consume** in requests, tool calls and tokens. These answer different
questions and are configured separately.

### Errors are a hierarchy, not a bag of fields

`ChatServiceError` subclasses each own an `ErrorCode` and an HTTP status, so no
component passes codes, statuses and messages down through the service, the
stream and the HTTP layer. `ChatErrorPayload` is the single wire form, used
identically by the HTTP error response and the SSE `error` event, and
`error_from_payload` reverses it so the non-streaming route can re-raise what
its streaming counterpart reported.

A bad tool argument is deliberately not an error: tools raise `ModelRetry` for
mistakes the model can fix, such as an item code that is not comparable, so the
run continues instead of failing.

### FastAPI, and in-memory conversations

`starlette`, `sse-starlette` and `uvicorn` already resolved as transitive
dependencies of pydantic-ai, so plain FastAPI cost exactly one additional
wheel. It was chosen over bare Starlette because `CONTRIBUTING.md` names
incoming HTTP bodies as the place Pydantic belongs, which is what FastAPI does
for free, and because the generated OpenAPI schema is a genuine portfolio
asset.

Conversations are stored in memory behind a `ConversationStore` protocol. A
Postgres-backed store can replace it without touching the service, and adding
conversation tables now would mean shipping schema for a feature with no
analytical requirement yet.

## Consequences

Grocery price questions can be asked in plain language, in Hebrew or English,
and the answer is auditable: the tool calls, the SQL parameters, and the exact
context sent to the model are all observable.

The service reads the remote analytical layer only. Store-level price history
and promotions live in the local database and are not reachable from chat.

Category questions are limited by data, not code: `product_classification` is
empty until the SuperCompare promotion step runs, so `category_price_summary`
returns an explicit note instead of an empty result.

Conversations are lost on restart, which is acceptable for a locally served
single-user service and is the seam most likely to need replacing first.

`pydantic-ai-skills` is a third-party package (MIT, Douglas Trajano) that
declares only `pydantic-ai-slim>=1.105` with no upper bound, so its
compatibility with pydantic-ai 2.x is incidental rather than guaranteed. Pin it
more tightly if an upgrade breaks.

## Alternatives rejected

**A text-to-SQL agent.** Maximum flexibility, but it puts unreviewed SQL in
front of the database and makes wrong answers hard to distinguish from right
ones. The five fixed queries encode the analytical decisions that matter,
including tie handling.

**Reading the local ETL database.** More data, but it would put a chat service
on the ETL source of truth and require reasoning over per-store history to
answer questions the analytical layer already answers directly.

**Bare Starlette.** Zero new dependencies and entirely capable, but it costs
hand-written body validation and gives up the OpenAPI schema, to save one
wheel that FastAPI's own dependencies already pull in.
