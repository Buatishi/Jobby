import inspect
from collections.abc import Sequence
from typing import Any

from redis.asyncio import Redis

from app.config import settings

DOCUMENTS_BUCKET = "cv-documents"


def capture_exception(exc: Exception) -> None:
    try:
        import sentry_sdk

        if settings.sentry_dsn:
            sentry_sdk.capture_exception(exc)
    except Exception:
        return


async def maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def delete_storage_prefix(
    supabase: Any,
    owner_prefix: str,
    extra_paths: Sequence[str] = (),
) -> None:
    bucket = supabase.storage.from_(DOCUMENTS_BUCKET)
    prefix = owner_prefix.strip("/")

    async def collect(path: str) -> list[str]:
        entries = await maybe_await(bucket.list(path))
        files: list[str] = []
        for entry in entries or []:
            name = (
                entry.get("name")
                if isinstance(entry, dict)
                else getattr(entry, "name", None)
            )
            if not name:
                continue
            full_path = f"{path}/{name}".strip("/")
            metadata = (
                entry.get("metadata")
                if isinstance(entry, dict)
                else getattr(entry, "metadata", None)
            )
            is_folder = metadata is None and "." not in str(name)
            if is_folder:
                files.extend(await collect(full_path))
            else:
                files.append(full_path)
        return files

    paths = list(dict.fromkeys([*await collect(prefix), *extra_paths]))
    if paths:
        await maybe_await(bucket.remove(paths))


async def invalidate_user_redis(
    user_id: str,
    redis_client: Redis | None = None,
) -> None:
    client = redis_client or Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        keys: list[str] = []
        for pattern in ("ai_cache:*", f"rate:*:{user_id}:*"):
            cursor = 0
            while True:
                cursor, batch = await client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=500,
                )
                keys.extend(str(key) for key in batch)
                if cursor == 0:
                    break
        if keys:
            await client.delete(*keys)
    finally:
        if redis_client is None:
            await client.aclose()
