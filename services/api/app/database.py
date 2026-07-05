from functools import lru_cache

from supabase import AsyncClient, create_async_client

from app.config import settings


@lru_cache
def _get_supabase_credentials() -> tuple[str, str]:
    return settings.supabase_project_url, settings.supabase_service_role_key


async def get_supabase_client() -> AsyncClient:
    supabase_url, supabase_key = _get_supabase_credentials()
    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing Supabase service configuration.")

    return await create_async_client(supabase_url, supabase_key)
