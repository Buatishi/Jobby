from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from redis.asyncio import Redis
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
)


class RateLimitKind(StrEnum):
    JOBS = "jobs"
    ATS = "ats"
    KITS = "kits"


@dataclass(frozen=True)
class RateLimitRule:
    limit: int | None
    period: str


class RateLimitExceededError(Exception):
    def __init__(self, limit: int, reset_at: datetime) -> None:
        self.limit = limit
        self.reset_at = reset_at
        super().__init__(f"Rate limit exceeded: {limit}")


def _rule(kind: RateLimitKind, tier: str) -> RateLimitRule:
    premium = tier == "premium"
    if kind == RateLimitKind.JOBS:
        return RateLimitRule(limit=None if premium else 10, period="month")
    if kind == RateLimitKind.ATS:
        return RateLimitRule(limit=50 if premium else 5, period="day")
    return RateLimitRule(limit=10 if premium else 0, period="month")


def _period_key(kind: RateLimitKind, now: datetime) -> str:
    if kind == RateLimitKind.ATS:
        return now.strftime("%Y-%m-%d")
    return now.strftime("%Y-%m")


def _reset_at(period: str, now: datetime) -> datetime:
    if period == "day":
        tomorrow = now.date() + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=UTC)

    last_day = monthrange(now.year, now.month)[1]
    if now.day == last_day:
        return datetime(now.year, now.month, now.day, tzinfo=UTC) + timedelta(days=1)
    next_month = now.replace(day=last_day, hour=0, minute=0, second=0, microsecond=0)
    return next_month + timedelta(days=1)


def _ttl_seconds(period: str, now: datetime) -> int:
    return max(1, int((_reset_at(period, now) - now).total_seconds()))


async def increment_rate_limit(
    user_id: str,
    tier: str,
    kind: RateLimitKind,
    redis_client: Redis | None = None,
) -> int:
    now = datetime.now(UTC)
    rule = _rule(kind, tier)
    if rule.limit is None:
        return 0
    if rule.limit <= 0:
        raise RateLimitExceededError(
            limit=rule.limit,
            reset_at=_reset_at(rule.period, now),
        )

    client = redis_client or Redis.from_url(settings.redis_url, decode_responses=True)
    key = f"rate:{kind.value}:{user_id}:{_period_key(kind, now)}"
    try:
        value = await client.incr(key)
        if value == 1:
            await client.expire(key, _ttl_seconds(rule.period, now))
    finally:
        if redis_client is None:
            await client.aclose()

    if int(value) > rule.limit:
        raise RateLimitExceededError(
            limit=rule.limit,
            reset_at=_reset_at(rule.period, now),
        )
    return int(value)
