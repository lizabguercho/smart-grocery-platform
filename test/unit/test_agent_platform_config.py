"""Tests for agent platform configuration."""

from __future__ import annotations

import pytest

from src.agent_platform.chat_service.models import AgentConfig, UsageBudget
from src.agent_platform.config import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_MAX_TOKENS,
    AgentPlatformConfig,
    RemoteDatabaseSettings,
    default_skills_directory,
)

REMOTE_ENV_VARS = (
    "REMOTE_DB_HOST",
    "REMOTE_DB_PORT",
    "REMOTE_DB_NAME",
    "REMOTE_DB_USER",
    "REMOTE_DB_PASSWORD",
)
AGENT_ENV_VARS = (
    "AGENT_MODEL",
    "AGENT_TEMPERATURE",
    "AGENT_MAX_TOKENS",
    "AGENT_TOP_P",
    "AGENT_REQUEST_LIMIT",
    "AGENT_TOOL_CALLS_LIMIT",
    "AGENT_TOTAL_TOKENS_LIMIT",
    "AGENT_RATE_LIMIT_REQUESTS_PER_MINUTE",
    "AGENT_RATE_LIMIT_BURST",
    "AGENT_HISTORY_MAX_MESSAGES",
    "AGENT_HISTORY_MAX_CHARS",
    "AGENT_SQL_STATEMENT_TIMEOUT_MS",
)


@pytest.fixture
def clean_env(monkeypatch) -> None:
    """Remove every variable the platform reads, then set the required ones."""

    for name in REMOTE_ENV_VARS + AGENT_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("REMOTE_DB_HOST", "db.example")


def test_from_env_uses_defaults_when_only_host_is_set(clean_env) -> None:
    config = AgentPlatformConfig.from_env()

    assert config.agent.model == DEFAULT_AGENT_MODEL
    assert config.agent.max_tokens == DEFAULT_MAX_TOKENS
    assert config.database.host == "db.example"


def test_from_env_reads_overrides(clean_env, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MODEL", "anthropic:claude-sonnet-4-5")
    monkeypatch.setenv("AGENT_MAX_TOKENS", "512")
    monkeypatch.setenv("AGENT_RATE_LIMIT_BURST", "2")
    monkeypatch.setenv("AGENT_HISTORY_MAX_MESSAGES", "6")

    config = AgentPlatformConfig.from_env()

    assert config.agent.model == "anthropic:claude-sonnet-4-5"
    assert config.agent.max_tokens == 512
    assert config.rate_limit.burst == 2
    assert config.history.max_messages == 6


def test_from_env_requires_the_remote_host(monkeypatch) -> None:
    monkeypatch.setenv("REMOTE_DB_HOST", "")

    with pytest.raises(ValueError, match="REMOTE_DB_HOST"):
        AgentPlatformConfig.from_env()


def test_from_env_rejects_a_non_numeric_limit(clean_env, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MAX_TOKENS", "plenty")

    with pytest.raises(ValueError, match="AGENT_MAX_TOKENS"):
        AgentPlatformConfig.from_env()


def test_blank_override_falls_back_to_the_default(clean_env, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MODEL", "   ")

    assert AgentPlatformConfig.from_env().agent.model == DEFAULT_AGENT_MODEL


def test_conninfo_enforces_read_only_and_a_statement_timeout() -> None:
    settings = RemoteDatabaseSettings(
        host="db.example",
        port=5432,
        dbname="postgres",
        user="contributor",
        password="secret",
        statement_timeout_ms=1234,
    )

    conninfo = settings.to_conninfo()

    assert "default_transaction_read_only=on" in conninfo
    assert "statement_timeout=1234" in conninfo
    assert "host=db.example" in conninfo


def test_agent_config_maps_onto_model_settings() -> None:
    settings = AgentConfig(
        model="openai:gpt-5.2",
        temperature=0.3,
        max_tokens=100,
        top_p=0.9,
        frequency_penalty=0.1,
        presence_penalty=0.2,
    ).to_model_settings()

    assert settings["temperature"] == 0.3
    assert settings["max_tokens"] == 100
    assert settings["top_p"] == 0.9
    # ModelSettings has no `model` key; the model is an Agent constructor
    # argument, so it must not leak into per-request settings.
    assert "model" not in settings


def test_usage_budget_maps_onto_usage_limits() -> None:
    limits = UsageBudget(
        request_limit=3, tool_calls_limit=4, total_tokens_limit=5
    ).to_usage_limits()

    assert limits.request_limit == 3
    assert limits.tool_calls_limit == 4
    assert limits.total_tokens_limit == 5


def test_skills_directory_exists() -> None:
    assert default_skills_directory().is_dir()
