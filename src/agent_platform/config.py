"""Configuration for the agent platform.

Every URL, timeout, limit, default and user-facing message the platform uses is
a named constant here, per CONTRIBUTING.md. `AgentPlatformConfig.from_env`
is the only place environment variables are read.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from src.agent_platform.chat_service.models import (
    AgentConfig,
    HistoryBudget,
    RateLimitPolicy,
    UsageBudget,
)

load_dotenv()

AGENT_MODEL_ENV = "AGENT_MODEL"
AGENT_TEMPERATURE_ENV = "AGENT_TEMPERATURE"
AGENT_MAX_TOKENS_ENV = "AGENT_MAX_TOKENS"
AGENT_TOP_P_ENV = "AGENT_TOP_P"
AGENT_REQUEST_LIMIT_ENV = "AGENT_REQUEST_LIMIT"
AGENT_TOOL_CALLS_LIMIT_ENV = "AGENT_TOOL_CALLS_LIMIT"
AGENT_TOTAL_TOKENS_LIMIT_ENV = "AGENT_TOTAL_TOKENS_LIMIT"
AGENT_RATE_LIMIT_RPM_ENV = "AGENT_RATE_LIMIT_REQUESTS_PER_MINUTE"
AGENT_RATE_LIMIT_BURST_ENV = "AGENT_RATE_LIMIT_BURST"
AGENT_HISTORY_MAX_MESSAGES_ENV = "AGENT_HISTORY_MAX_MESSAGES"
AGENT_HISTORY_MAX_CHARS_ENV = "AGENT_HISTORY_MAX_CHARS"
AGENT_SQL_STATEMENT_TIMEOUT_ENV = "AGENT_SQL_STATEMENT_TIMEOUT_MS"

REMOTE_DB_HOST_ENV = "REMOTE_DB_HOST"
REMOTE_DB_PORT_ENV = "REMOTE_DB_PORT"
REMOTE_DB_NAME_ENV = "REMOTE_DB_NAME"
REMOTE_DB_USER_ENV = "REMOTE_DB_USER"
REMOTE_DB_PASSWORD_ENV = "REMOTE_DB_PASSWORD"

DEFAULT_AGENT_MODEL = "openai:gpt-5.2"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TOP_P = 1.0

DEFAULT_REQUEST_LIMIT = 12
DEFAULT_TOOL_CALLS_LIMIT = 20
DEFAULT_TOTAL_TOKENS_LIMIT = 120_000

DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE = 20
DEFAULT_RATE_LIMIT_BURST = 5

DEFAULT_HISTORY_MAX_MESSAGES = 40
DEFAULT_HISTORY_MAX_CHARACTERS = 60_000

DEFAULT_SQL_STATEMENT_TIMEOUT_MS = 15_000
DEFAULT_REMOTE_DB_PORT = 5432
DEFAULT_REMOTE_DB_NAME = "postgres"
DEFAULT_CONNECT_TIMEOUT_SECONDS = 15

DEFAULT_POOL_MIN_SIZE = 1
DEFAULT_POOL_MAX_SIZE = 4

SESSION_OPTIONS_TEMPLATE = (
    "-c statement_timeout={statement_timeout_ms} -c default_transaction_read_only=on"
)

SKILLS_DIRECTORY_NAME = "skills"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
SERVER_HOST_ENV = "AGENT_SERVER_HOST"
SERVER_PORT_ENV = "AGENT_SERVER_PORT"

MISSING_REMOTE_HOST_MESSAGE = (
    f"{REMOTE_DB_HOST_ENV} is not set. The chat service queries the shared "
    "analytical database; copy .env.example to .env and fill the REMOTE_DB_* "
    "values."
)
INVALID_NUMBER_MESSAGE = "{name}={value!r} is not a valid {kind}."


def _read_int(name: str, default: int) -> int:
    """Read an integer environment variable, falling back to `default`."""

    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as error:
        raise ValueError(
            INVALID_NUMBER_MESSAGE.format(name=name, value=raw, kind="integer")
        ) from error


def _read_float(name: str, default: float) -> float:
    """Read a float environment variable, falling back to `default`."""

    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as error:
        raise ValueError(
            INVALID_NUMBER_MESSAGE.format(name=name, value=raw, kind="number")
        ) from error


def _read_str(name: str, default: str) -> str:
    """Read a string environment variable, falling back to `default`."""

    raw = os.getenv(name)
    return raw.strip() if raw and raw.strip() else default


@dataclass(frozen=True)
class RemoteDatabaseSettings:
    """Connection settings for the shared analytical database.

    The chat service reads the remote analytical layer rather than the local
    ETL database, matching the split documented in
    docs/client-server-architecture.md.
    """

    host: str
    port: int
    dbname: str
    user: str
    password: str
    statement_timeout_ms: int
    connect_timeout_seconds: int = DEFAULT_CONNECT_TIMEOUT_SECONDS
    pool_min_size: int = DEFAULT_POOL_MIN_SIZE
    pool_max_size: int = DEFAULT_POOL_MAX_SIZE

    def to_conninfo(self) -> str:
        """Build a libpq connection string.

        `default_transaction_read_only` and `statement_timeout` are set as
        server-side session options rather than client-side flags, so no tool
        can write to the database or run an unbounded query even if it tries.

        The password is included because psycopg needs it; this string must
        never be logged.
        """

        options = SESSION_OPTIONS_TEMPLATE.format(
            statement_timeout_ms=self.statement_timeout_ms
        )
        parts = {
            "host": self.host,
            "port": str(self.port),
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
            "connect_timeout": str(self.connect_timeout_seconds),
            "options": f"'{options}'",
        }
        return " ".join(f"{key}={value}" for key, value in parts.items() if value)

    @classmethod
    def from_env(cls, statement_timeout_ms: int) -> RemoteDatabaseSettings:
        """Build settings from the REMOTE_DB_* environment variables."""

        host = os.getenv(REMOTE_DB_HOST_ENV, "").strip()
        if not host:
            raise ValueError(MISSING_REMOTE_HOST_MESSAGE)
        return cls(
            host=host,
            port=_read_int(REMOTE_DB_PORT_ENV, DEFAULT_REMOTE_DB_PORT),
            dbname=_read_str(REMOTE_DB_NAME_ENV, DEFAULT_REMOTE_DB_NAME),
            user=os.getenv(REMOTE_DB_USER_ENV, "").strip(),
            password=os.getenv(REMOTE_DB_PASSWORD_ENV, ""),
            statement_timeout_ms=statement_timeout_ms,
        )


@dataclass(frozen=True)
class AgentPlatformConfig:
    """Everything the chat service needs to start."""

    agent: AgentConfig
    usage: UsageBudget
    rate_limit: RateLimitPolicy
    history: HistoryBudget
    database: RemoteDatabaseSettings
    skills_directory: Path
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    @classmethod
    def from_env(cls) -> AgentPlatformConfig:
        """Build the platform configuration from the environment."""

        statement_timeout_ms = _read_int(
            AGENT_SQL_STATEMENT_TIMEOUT_ENV, DEFAULT_SQL_STATEMENT_TIMEOUT_MS
        )
        return cls(
            agent=AgentConfig(
                model=_read_str(AGENT_MODEL_ENV, DEFAULT_AGENT_MODEL),
                temperature=_read_float(AGENT_TEMPERATURE_ENV, DEFAULT_TEMPERATURE),
                max_tokens=_read_int(AGENT_MAX_TOKENS_ENV, DEFAULT_MAX_TOKENS),
                top_p=_read_float(AGENT_TOP_P_ENV, DEFAULT_TOP_P),
            ),
            usage=UsageBudget(
                request_limit=_read_int(AGENT_REQUEST_LIMIT_ENV, DEFAULT_REQUEST_LIMIT),
                tool_calls_limit=_read_int(
                    AGENT_TOOL_CALLS_LIMIT_ENV, DEFAULT_TOOL_CALLS_LIMIT
                ),
                total_tokens_limit=_read_int(
                    AGENT_TOTAL_TOKENS_LIMIT_ENV, DEFAULT_TOTAL_TOKENS_LIMIT
                ),
            ),
            rate_limit=RateLimitPolicy(
                requests_per_minute=_read_int(
                    AGENT_RATE_LIMIT_RPM_ENV, DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE
                ),
                burst=_read_int(AGENT_RATE_LIMIT_BURST_ENV, DEFAULT_RATE_LIMIT_BURST),
            ),
            history=HistoryBudget(
                max_messages=_read_int(
                    AGENT_HISTORY_MAX_MESSAGES_ENV, DEFAULT_HISTORY_MAX_MESSAGES
                ),
                max_characters=_read_int(
                    AGENT_HISTORY_MAX_CHARS_ENV, DEFAULT_HISTORY_MAX_CHARACTERS
                ),
            ),
            database=RemoteDatabaseSettings.from_env(statement_timeout_ms),
            skills_directory=default_skills_directory(),
            host=_read_str(SERVER_HOST_ENV, DEFAULT_HOST),
            port=_read_int(SERVER_PORT_ENV, DEFAULT_PORT),
        )


def default_skills_directory() -> Path:
    """Return the directory holding the platform's SKILL.md playbooks."""

    return Path(__file__).parent / SKILLS_DIRECTORY_NAME
