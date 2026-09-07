"""Tests for the chat request rate limiter.

Time is driven by a list-backed clock, so these tests never sleep and never
depend on wall-clock timing.
"""

from __future__ import annotations

import pytest

from src.agent_platform.chat_service.models import RateLimitPolicy
from src.agent_platform.errors import RateLimitExceededError
from src.agent_platform.rate_limit import RateLimiter

CONVERSATION = "conversation-1"


class FakeClock:
    """A monotonic clock the test advances by hand."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def make_limiter(clock: FakeClock, burst: int = 2, rpm: int = 60) -> RateLimiter:
    return RateLimiter(
        RateLimitPolicy(requests_per_minute=rpm, burst=burst), clock=clock
    )


@pytest.mark.anyio
async def test_burst_requests_are_admitted(clock: FakeClock) -> None:
    limiter = make_limiter(clock, burst=3)

    for _ in range(3):
        await limiter.acquire(CONVERSATION)


@pytest.mark.anyio
async def test_exhausted_bucket_is_rejected(clock: FakeClock) -> None:
    limiter = make_limiter(clock, burst=1)
    await limiter.acquire(CONVERSATION)

    with pytest.raises(RateLimitExceededError) as caught:
        await limiter.acquire(CONVERSATION)

    assert caught.value.retry_after == pytest.approx(1.0)


@pytest.mark.anyio
async def test_bucket_refills_over_time(clock: FakeClock) -> None:
    limiter = make_limiter(clock, burst=1, rpm=60)
    await limiter.acquire(CONVERSATION)
    clock.advance(1.0)

    await limiter.acquire(CONVERSATION)


@pytest.mark.anyio
async def test_refill_is_capped_at_the_burst_size(clock: FakeClock) -> None:
    limiter = make_limiter(clock, burst=2, rpm=60)
    await limiter.acquire(CONVERSATION)
    clock.advance(3600.0)

    await limiter.acquire(CONVERSATION)
    await limiter.acquire(CONVERSATION)

    with pytest.raises(RateLimitExceededError):
        await limiter.acquire(CONVERSATION)


@pytest.mark.anyio
async def test_conversations_have_independent_buckets(clock: FakeClock) -> None:
    limiter = make_limiter(clock, burst=1)
    await limiter.acquire(CONVERSATION)

    await limiter.acquire("conversation-2")


@pytest.mark.anyio
async def test_retry_after_scales_with_the_rate(clock: FakeClock) -> None:
    limiter = make_limiter(clock, burst=1, rpm=30)
    await limiter.acquire(CONVERSATION)

    with pytest.raises(RateLimitExceededError) as caught:
        await limiter.acquire(CONVERSATION)

    assert caught.value.retry_after == pytest.approx(2.0)


@pytest.mark.anyio
async def test_forgetting_a_key_resets_its_bucket(clock: FakeClock) -> None:
    limiter = make_limiter(clock, burst=1)
    await limiter.acquire(CONVERSATION)

    await limiter.forget(CONVERSATION)

    await limiter.acquire(CONVERSATION)
