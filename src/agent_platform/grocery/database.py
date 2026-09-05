"""Async, read-only access to the shared grocery analytical database.

The pool is opened once at application startup and shared by every tool call.
Read-only and statement-timeout are enforced server-side through libpq session
options (see `RemoteDatabaseSettings.to_conninfo`), so a tool cannot write or
run an unbounded query regardless of the SQL it is given.

`psycopg.Error` is translated into `DatabaseUnavailableError` here so callers
never have to know which driver is underneath, and so the message shown to a
client never carries connection details.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import psycopg
from psycopg_pool import AsyncConnectionPool

from src.agent_platform.config import RemoteDatabaseSettings
from src.agent_platform.errors import DatabaseUnavailableError

LOGGER = logging.getLogger(__name__)

POOL_NAME = "agent-platform-grocery"
QUERY_FAILED_MESSAGE = "The grocery database could not answer the query."
POOL_CLOSED_MESSAGE = "The grocery database connection pool is not open."
QUERY_FAILED_LOG = "Grocery query failed: %s"


class AsyncGroceryDatabase:
    """A pooled, read-only connection to the analytical `grocery` schema."""

    def __init__(self, settings: RemoteDatabaseSettings) -> None:
        self._settings = settings
        self._pool: AsyncConnectionPool | None = None

    async def open(self) -> None:
        """Open the connection pool and wait for it to be usable."""

        if self._pool is not None:
            return
        pool = AsyncConnectionPool(
            self._settings.to_conninfo(),
            min_size=self._settings.pool_min_size,
            max_size=self._settings.pool_max_size,
            name=POOL_NAME,
            open=False,
        )
        await pool.open(wait=True, timeout=self._settings.connect_timeout_seconds)
        self._pool = pool

    async def close(self) -> None:
        """Close the connection pool."""

        if self._pool is None:
            return
        await self._pool.close()
        self._pool = None

    async def fetch_all(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[tuple[Any, ...]]:
        """Run a parameterized query and return every row.

        Raises:
            DatabaseUnavailableError: If the pool is closed or the query fails.
        """

        if self._pool is None:
            raise DatabaseUnavailableError(POOL_CLOSED_MESSAGE)
        try:
            async with (
                self._pool.connection() as connection,
                connection.cursor() as cursor,
            ):
                await cursor.execute(sql, params)
                return await cursor.fetchall()
        except psycopg.Error as error:
            # Logged at exception level for the operator; the client sees only
            # the generic message, since driver errors can echo the conninfo.
            LOGGER.exception(QUERY_FAILED_LOG, type(error).__name__)
            raise DatabaseUnavailableError(QUERY_FAILED_MESSAGE) from error

    async def fetch_one(
        self, sql: str, params: Sequence[Any] = ()
    ) -> tuple[Any, ...] | None:
        """Run a parameterized query and return the first row, if any."""

        rows = await self.fetch_all(sql, params)
        return rows[0] if rows else None
