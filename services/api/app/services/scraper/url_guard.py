"""Guarda contra SSRF para las URLs que el servidor visita con un navegador.

Un usuario puede pedir que analicemos una URL. Sin controles, esa URL podría apuntar
a servicios internos (localhost, la red privada del proveedor, metadatos de la nube).
Acá se exige http(s), sin credenciales, en puertos web y con todas las IP públicas.
"""

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit

MAX_URL_LENGTH = 2048
_ALLOWED_SCHEMES = {"http", "https"}
_ALLOWED_PORTS = {None, 80, 443}
_BLOCKED_HOST_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home.arpa")
_LINKEDIN_DOMAIN = "linkedin.com"


class UnsafeUrlError(ValueError):
    """La URL apunta a un destino que el servidor no debe visitar."""


def _is_public_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


async def _resolve(host: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeUrlError("No se pudo resolver el host de la URL.") from exc
    return [str(info[4][0]) for info in infos]


async def ensure_public_http_url(url: str) -> str:
    candidate = url.strip()
    if not candidate or len(candidate) > MAX_URL_LENGTH:
        raise UnsafeUrlError("La URL está vacía o es demasiado larga.")

    parts = urlsplit(candidate)
    scheme = parts.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError("Solo se permiten URLs http o https.")
    host = (parts.hostname or "").lower()
    if not host:
        raise UnsafeUrlError("La URL no tiene host.")
    if parts.username or parts.password:
        raise UnsafeUrlError("La URL no puede incluir credenciales.")
    try:
        port = parts.port
    except ValueError as exc:
        raise UnsafeUrlError("El puerto de la URL no es válido.") from exc
    if port not in _ALLOWED_PORTS:
        raise UnsafeUrlError("Solo se permiten los puertos web estándar.")
    if host == "localhost" or host.endswith(_BLOCKED_HOST_SUFFIXES):
        raise UnsafeUrlError("El host de la URL no es público.")

    if _is_ip_literal(host):
        addresses = [host]
    else:
        addresses = await _resolve(host, port or (443 if scheme == "https" else 80))
    if not addresses or not all(_is_public_address(address) for address in addresses):
        raise UnsafeUrlError("El host de la URL no es público.")
    return candidate


def ensure_linkedin_host(url: str) -> None:
    host = (urlsplit(url.strip()).hostname or "").lower()
    if host != _LINKEDIN_DOMAIN and not host.endswith(f".{_LINKEDIN_DOMAIN}"):
        raise UnsafeUrlError("La URL debe ser de linkedin.com.")


def make_route_guard() -> Callable[[Any], Awaitable[None]]:
    """Handler de ``page.route`` que aborta pedidos a destinos no públicos.

    Se aplica a cada request del navegador para cubrir también las redirecciones.
    """

    verdicts: dict[tuple[str, str, int | None], bool] = {}

    async def guard(route: Any) -> None:
        url = str(route.request.url)
        if url.startswith(("data:", "blob:", "about:")):
            await route.continue_()
            return
        parts = urlsplit(url)
        key = (parts.scheme.lower(), (parts.hostname or "").lower(), parts.port)
        allowed = verdicts.get(key)
        if allowed is None:
            try:
                await ensure_public_http_url(url)
                allowed = True
            except UnsafeUrlError:
                allowed = False
            verdicts[key] = allowed
        if allowed:
            await route.continue_()
        else:
            await route.abort()

    return guard
