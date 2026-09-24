import asyncio
import weakref
from functools import lru_cache

from supabase import AsyncClient, create_async_client

from app.config import settings

# Un cliente por event loop. Reutilizarlo conserva las conexiones HTTPS con Supabase
# entre pedidos, en vez de abrir una nueva (con su TLS) en cada llamada. Las tareas en
# modo local corren en otro hilo con su propio loop, y un cliente httpx no se comparte
# entre loops: cada loop recibe el suyo, que se libera cuando el loop desaparece.
_clients: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, AsyncClient] = (
    weakref.WeakKeyDictionary()
)


@lru_cache
def _get_supabase_credentials() -> tuple[str, str]:
    return settings.supabase_project_url, settings.supabase_service_role_key


async def get_supabase_client() -> AsyncClient:
    supabase_url, supabase_key = _get_supabase_credentials()
    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing Supabase service configuration.")

    loop = asyncio.get_running_loop()
    client = _clients.get(loop)
    if client is None:
        client = await create_async_client(supabase_url, supabase_key)
        _clients[loop] = client
    return client
