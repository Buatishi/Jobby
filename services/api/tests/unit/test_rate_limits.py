"""Límites de uso por plan, contra el Redis en memoria de `conftest.py`."""

import pytest

from app.services.rate_limits import (
    RateLimitExceededError,
    RateLimitKind,
    increment_rate_limit,
)
from tests.fakes import FakeRedis


@pytest.mark.asyncio
async def test_free_ats_allows_five_reports_a_day_and_blocks_the_sixth(
    fake_redis: FakeRedis,
) -> None:
    counts = [
        await increment_rate_limit("user-1", "free", RateLimitKind.ATS)
        for _ in range(5)
    ]

    with pytest.raises(RateLimitExceededError) as exceeded:
        await increment_rate_limit("user-1", "free", RateLimitKind.ATS)

    assert counts == [1, 2, 3, 4, 5]
    assert exceeded.value.limit == 5
    (key,) = fake_redis.values
    assert key.startswith("rate:ats:user-1:")
    # El contador vence solo: la clave recibe su tiempo de vida con el primer uso.
    assert 0 < fake_redis.ttls[key] <= 24 * 60 * 60


@pytest.mark.asyncio
async def test_premium_jobs_have_no_limit_and_do_not_touch_redis(
    fake_redis: FakeRedis,
) -> None:
    assert await increment_rate_limit("user-1", "premium", RateLimitKind.JOBS) == 0
    assert fake_redis.values == {}


@pytest.mark.asyncio
async def test_interview_kits_are_blocked_on_the_free_plan(
    fake_redis: FakeRedis,
) -> None:
    with pytest.raises(RateLimitExceededError):
        await increment_rate_limit("user-1", "free", RateLimitKind.KITS)

    assert fake_redis.values == {}


@pytest.mark.asyncio
async def test_each_person_has_its_own_counter(fake_redis: FakeRedis) -> None:
    await increment_rate_limit("user-1", "free", RateLimitKind.JOBS)
    await increment_rate_limit("user-2", "free", RateLimitKind.JOBS)

    assert sorted(fake_redis.values.values()) == ["1", "1"]


@pytest.mark.asyncio
async def test_free_jobs_allow_ten_a_month_and_block_the_eleventh(
    fake_redis: FakeRedis,
) -> None:
    counts = [
        await increment_rate_limit("user-1", "free", RateLimitKind.JOBS)
        for _ in range(10)
    ]

    with pytest.raises(RateLimitExceededError) as exceeded:
        await increment_rate_limit("user-1", "free", RateLimitKind.JOBS)

    assert counts == list(range(1, 11))
    assert exceeded.value.limit == 10
