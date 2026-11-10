"""Tope por IP a los pedidos sin sesión (Decisión 46).

La API tiene su propia dirección pública y limitaba solo por usuario con sesión: quien
le pegaba directo sin sesión no tenía freno. Solo tres de sus rutas responden sin
sesión (`/health`, `/api/v1/health` y el aviso de pago de LemonSqueezy); el resto
contesta 401, así que quien insiste sin sesión es un escáner o un bucle, no una
persona.

Dos decisiones lo hacen seguro de dejar prendido:

- **Solo cuenta pedidos sin encabezado `Authorization`.** Una persona con sesión nunca
  entra en este contador, aunque su IP se identificara mal: lo peor que puede pasar
  con una IP mal leída es frenar pedidos basura juntos.
- **Sin una IP usable no limita.** Ni Render ni Vercel dan una IP del cliente que se
  pueda dar por segura, así que se lee la primera de `X-Forwarded-For` (la que Vercel
  pone y Render conserva) y se descarta si es interna: la de un proxy juntaría a todos
  en un contador. La dirección de la conexión no se usa nunca (en Render es la del
  balanceador). Quien le pega directo a Render puede falsear ese encabezado: esto
  frena a un escáner o a un bucle, no a un ataque decidido, que necesita un firewall
  delante.

Si Redis falla, el pedido pasa: un fallo de este tope no puede dejar a nadie sin
servicio.
"""

import ipaddress
import logging
import time
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

logger = logging.getLogger("jobmatch.api")

# Muy por encima de cualquier uso real sin sesión: nadie legítimo llega acá.
IP_LIMIT_PER_MINUTE = 60
WINDOW_SECONDS = 60
# El contador de una ventana no sirve cuando pasa; el margen cubre el reloj de Redis.
COUNTER_TTL_SECONDS = 2 * WINDOW_SECONDS
# Este tope no puede sumarle espera a nadie: con Redis lento se deja pasar el pedido.
REDIS_TIMEOUT_SECONDS = 1.0

# Las únicas rutas que responden sin sesión. Render y las revisiones de estado piden
# `/health` todo el día, y LemonSqueezy avisa los pagos por el webhook: ninguna puede
# quedar con un 429.
EXEMPT_PATHS = frozenset({"/health", "/api/v1/health"})
EXEMPT_PREFIXES = ("/api/v1/webhooks/",)


def _now() -> float:
    return time.time()


def client_ip(request: Request) -> str | None:
    """La IP con la que se cuenta el pedido, o `None` si no hay una usable.

    Una dirección IPv6 cuenta como su red /64: quien tiene IPv6 recibe una red entera
    y contar por dirección le dejaría rotarla.
    """
    first = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not first:
        return None
    try:
        address = ipaddress.ip_address(first)
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    # Interna, de documentación o reservada: es la de un proxy, no la de una persona.
    if not address.is_global:
        return None
    if isinstance(address, ipaddress.IPv6Address):
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return str(address)


def _is_exempt(path: str) -> bool:
    return path in EXEMPT_PATHS or path.startswith(EXEMPT_PREFIXES)


async def _count_request(ip: str) -> tuple[int, int]:
    """Cuenta un pedido de esta IP en el minuto: (pedidos, segundos que faltan)."""
    now = _now()
    window = int(now // WINDOW_SECONDS)
    retry_after = max(1, WINDOW_SECONDS - int(now % WINDOW_SECONDS))
    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=REDIS_TIMEOUT_SECONDS,
        socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
    )
    try:
        key = f"rate:ip:{ip}:{window}"
        count = int(await client.incr(key))
        if count == 1:
            await client.expire(key, COUNTER_TTL_SECONDS)
    finally:
        await client.aclose()
    return count, retry_after


class IpRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if (
            not settings.ip_rate_limit_enabled
            or request.method == "OPTIONS"
            or request.headers.get("authorization")
            or _is_exempt(request.url.path)
        ):
            return await call_next(request)

        ip = client_ip(request)
        if ip is None:
            return await call_next(request)

        try:
            count, retry_after = await _count_request(ip)
        except Exception as exc:
            # Un fallo de Redis no puede dejar a nadie sin servicio. Sin la IP en log.
            logger.warning("No se pudo contar el pedido por IP: %s", type(exc).__name__)
            return await call_next(request)

        if count > IP_LIMIT_PER_MINUTE:
            if count == IP_LIMIT_PER_MINUTE + 1:
                # Una vez por ventana y sin la IP: sirve para ver que el tope actúa.
                logger.warning(
                    "Tope por IP: más de %s pedidos sin sesión en un minuto",
                    IP_LIMIT_PER_MINUTE,
                )
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error": "Demasiados pedidos sin sesión. Probá en un rato.",
                    "code": "IP_RATE_LIMIT_EXCEEDED",
                    "details": {"retry_after_seconds": retry_after},
                },
            )
        return await call_next(request)
