import inspect
from collections.abc import Sequence
from typing import Any

from redis.asyncio import Redis

from app.config import settings

DOCUMENTS_BUCKET = "cv-documents"
# `list()` de Storage devuelve 100 entradas por llamada si no se pide otra página: sin
# paginar, una carpeta con más archivos se borraba solo hasta la primera página.
STORAGE_PAGE_SIZE = 100
# Tope de páginas por carpeta, por si un Storage ignorara `offset` y repitiera la misma.
MAX_STORAGE_PAGES = 200
REMOVE_BATCH_SIZE = 100


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

    async def list_all(path: str) -> list[Any]:
        entries: list[Any] = []
        for page_number in range(MAX_STORAGE_PAGES):
            options = {
                "limit": STORAGE_PAGE_SIZE,
                "offset": page_number * STORAGE_PAGE_SIZE,
            }
            page = await maybe_await(bucket.list(path, options))
            entries.extend(page or [])
            if len(page or []) < STORAGE_PAGE_SIZE:
                break
        return entries

    async def collect(path: str) -> list[str]:
        entries = await list_all(path)
        files: list[str] = []
        for entry in entries:
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
    await remove_storage_objects(supabase, paths)


async def remove_storage_objects(supabase: Any, paths: Sequence[str]) -> None:
    """Borra archivos del bucket de CV, de a lotes para no armar un pedido gigante."""
    bucket = supabase.storage.from_(DOCUMENTS_BUCKET)
    unique = list(dict.fromkeys(path for path in paths if path))
    for start in range(0, len(unique), REMOVE_BATCH_SIZE):
        await maybe_await(bucket.remove(unique[start : start + REMOVE_BATCH_SIZE]))


async def invalidate_user_redis(
    user_id: str,
    redis_client: Redis | None = None,
) -> None:
    client = redis_client or Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        keys: list[str] = []
        for pattern in (f"rate:*:{user_id}:*",):
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
