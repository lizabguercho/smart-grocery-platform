"""Rate limiting for incoming chat requests.

A token bucket per conversation: `burst` requests may arrive at once, after
which requests are admitted at `requests_per_minute`. Rejection is immediate
rather than queued, so a caller learns to back off instead of accumulating
hidden latency, and is told how long to wait.

This bounds how often a run may *start*. What a single run may consume once
started is bounded separately by `UsageBudget`, which pydantic-ai enforces.

The clock is injected so tests can advance time without sleeping, matching the
approach already used by the SuperCompare client.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass

from src.agent_platform.chat_service.models import RateLimitPolicy
from src.agent_platform.errors import RateLimitExceededError

RATE_LIMITED_MESSAGE = (
    "Too many requests for this conversation. Retry in {retry_after:.1f}s."
)
RETRY_AFTER_PRECISION = 3


@dataclass
class _Bucket:
    """Token bucket state for one key."""

    tokens: float
    updated_at: float


class RateLimiter:
    """Per-key token bucket over chat requests."""

    def __init__(
        self,
        policy: RateLimitPolicy,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._policy = policy
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, key: str) -> None:
        """Consume one token for `key`.

        Raises:
            RateLimitExceededError: If the bucket is empty, carrying the wait
                needed before the next token is available.
        """

        async with self._lock:
            now = self._clock()
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=float(self._policy.burst), updated_at=now)
                self._buckets[key] = bucket

            elapsed = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(
                float(self._policy.burst),
                bucket.tokens + elapsed * self._policy.refill_per_second,
            )
            bucket.updated_at = now

            if bucket.tokens < 1.0:
                missing = 1.0 - bucket.tokens
                retry_after = round(
                    missing / self._policy.refill_per_second, RETRY_AFTER_PRECISION
                )
                raise RateLimitExceededError(
                    RATE_LIMITED_MESSAGE.format(retry_after=retry_after),
                    retry_after=retry_after,
                )

            bucket.tokens -= 1.0

    async def forget(self, key: str) -> None:
        """Drop the bucket for `key`, so finished conversations do not leak."""

        async with self._lock:
            self._buckets.pop(key, None)
