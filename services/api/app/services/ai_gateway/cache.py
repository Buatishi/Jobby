import hashlib
import json
from typing import Any

from redis.asyncio import Redis

from app.config import settings

AI_CACHE_TTL_SECONDS = 24 * 60 * 60


def cache_key(task: str, input_data: str, profile_updated_at: str) -> str:
    digest = hashlib.sha256(
        f"{task}:{input_data}:{profile_updated_at}".encode()
    ).hexdigest()
    return f"ai:{task}:{digest}"


def create_redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def get_cached(redis: Redis, key: str) -> Any | None:
    cached = await redis.get(key)
    if cached is None:
        return None

    return json.loads(cached)


async def set_cached(
    redis: Redis,
    key: str,
    value: Any,
    ttl_seconds: int = AI_CACHE_TTL_SECONDS,
) -> None:
    await redis.set(key, json.dumps(value), ex=ttl_seconds)
