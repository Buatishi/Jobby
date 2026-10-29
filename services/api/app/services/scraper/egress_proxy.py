"""Proxy local por el que sale todo el tráfico del navegador del scraper.

La guarda de URLs (``url_guard``) resuelve el nombre de host para decidir si es
público y después Chromium lo vuelve a resolver para conectar. Un DNS controlado por el
atacante puede contestar una IP pública la primera vez y una interna (127.0.0.1, la red
privada del proveedor, los metadatos de la nube) la segunda: es el DNS rebinding, y el
navegador llega adonde la guarda había dicho que no.

Acá el navegador no resuelve nada: se lo lanza con este proxy, que resuelve el nombre
una sola vez, exige que todas las IP sean públicas y conecta a esas mismas direcciones.
No hay una segunda consulta que pueda cambiar. Como es el único camino de salida,
también cubre lo que ``page.route`` no ve (redirecciones, service workers, WebSockets,
recursos de otros orígenes). Los HTTPS pasan como túnel (CONNECT): el navegador sigue
validando el certificado del sitio de punta a punta.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Self
from urllib.parse import urlsplit

from app.services.scraper.url_guard import UnsafeUrlError, resolve_public_addresses

ALLOWED_PORTS = frozenset({80, 443})
# Cabecera de un pedido: 64 KB sobra para cualquier navegador.
MAX_HEAD_BYTES = 64 * 1024
HEAD_TIMEOUT_SECONDS = 15.0
CONNECT_TIMEOUT_SECONDS = 10.0
CLOSE_TIMEOUT_SECONDS = 2.0
_RELAY_CHUNK_BYTES = 64 * 1024
# Cabeceras que son del salto navegador -> proxy y no deben llegar al sitio.
_HOP_BY_HOP = frozenset(
    {
        "connection",
        "proxy-connection",
        "proxy-authorization",
        "keep-alive",
        "te",
        "trailer",
        "upgrade",
    }
)
_REASONS = {400: "Bad Request", 403: "Forbidden", 502: "Bad Gateway"}

Resolver = Callable[[str, int], Awaitable[list[str]]]
Streams = tuple[asyncio.StreamReader, asyncio.StreamWriter]
Connector = Callable[[str, int], Awaitable[Streams]]


class _BadRequestError(ValueError):
    """El pedido no es uno que un navegador le haga a un proxy."""


@dataclass(frozen=True)
class _Request:
    is_connect: bool
    host: str
    port: int
    # Lo que se le manda al sitio en un pedido HTTP plano (vacío en un túnel).
    head: bytes


def _split_authority(target: str) -> tuple[str, int]:
    if target.startswith("["):
        end = target.find("]")
        host, rest = target[1:end], target[end + 1 :]
        port_text = rest[1:] if rest.startswith(":") else ""
    else:
        host, _, port_text = target.rpartition(":")
    if not host or not port_text.isdigit():
        raise _BadRequestError("destino sin host o sin puerto")
    return host, int(port_text)


def _parse_request(raw_head: bytes) -> _Request:
    lines = raw_head[: -len(b"\r\n\r\n")].decode("latin-1").split("\r\n")
    parts = lines[0].split(" ")
    if len(parts) != 3 or not parts[2].startswith("HTTP/1."):
        raise _BadRequestError("línea de pedido inválida")
    method, target, _version = parts

    if method.upper() == "CONNECT":
        host, port = _split_authority(target)
        return _Request(is_connect=True, host=host, port=port, head=b"")

    try:
        url = urlsplit(target)
        port = url.port or 80
    except ValueError as exc:
        raise _BadRequestError("URL inválida") from exc
    # Un proxy recibe la URL completa; solo se reenvía http (https llega por CONNECT).
    if url.scheme.lower() != "http" or not url.hostname:
        raise _BadRequestError("el pedido no es una URL http completa")
    path = (url.path or "/") + (f"?{url.query}" if url.query else "")
    headers = [
        line
        for line in lines[1:]
        if line and line.split(":", 1)[0].strip().lower() not in _HOP_BY_HOP
    ]
    # Una conexión por pedido: así cada uno se valida y se conecta por separado.
    forwarded = [f"{method} {path} HTTP/1.1", *headers, "Connection: close", "", ""]
    return _Request(
        is_connect=False,
        host=url.hostname,
        port=port,
        head="\r\n".join(forwarded).encode("latin-1"),
    )


async def _pipe(source: asyncio.StreamReader, sink: asyncio.StreamWriter) -> None:
    try:
        while data := await source.read(_RELAY_CHUNK_BYTES):
            sink.write(data)
            await sink.drain()
    except (ConnectionError, OSError):
        pass


async def _close(writer: asyncio.StreamWriter | None) -> None:
    if writer is None:
        return
    writer.close()
    with contextlib.suppress(Exception):
        await writer.wait_closed()


class EgressProxy:
    """Proxy HTTP en 127.0.0.1 que solo conecta a IP públicas, validadas al conectar."""

    def __init__(
        self,
        *,
        resolve: Resolver = resolve_public_addresses,
        open_connection: Connector = asyncio.open_connection,
        allowed_ports: frozenset[int] = ALLOWED_PORTS,
    ) -> None:
        self._resolve = resolve
        self._open_connection = open_connection
        self._allowed_ports = allowed_ports
        self._server: asyncio.Server | None = None
        self._tasks: set[asyncio.Task[Any]] = set()

    @property
    def url(self) -> str:
        assert self._server is not None, "el proxy no está iniciado"
        port = self._server.sockets[0].getsockname()[1]
        return f"http://127.0.0.1:{port}"

    async def __aenter__(self) -> Self:
        self._server = await asyncio.start_server(
            self._on_client, "127.0.0.1", 0, limit=MAX_HEAD_BYTES
        )
        return self

    async def __aexit__(self, *_exc: object) -> None:
        assert self._server is not None
        self._server.close()
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(
                self._server.wait_closed(), timeout=CLOSE_TIMEOUT_SECONDS
            )

    async def _on_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        assert task is not None
        self._tasks.add(task)
        upstream_writer: asyncio.StreamWriter | None = None
        try:
            upstream = await self._open_tunnel_or_reply(reader, writer)
            if upstream is None:
                return
            upstream_reader, upstream_writer = upstream
            await self._relay(reader, writer, upstream_reader, upstream_writer)
        except (ConnectionError, OSError):
            pass  # El navegador o el sitio cortaron: no hay a quién avisar.
        finally:
            self._tasks.discard(task)
            await _close(upstream_writer)
            await _close(writer)

    async def _open_tunnel_or_reply(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> Streams | None:
        """Valida el pedido y abre la conexión; si falla, responde y devuelve None."""
        try:
            raw_head = await asyncio.wait_for(
                reader.readuntil(b"\r\n\r\n"), timeout=HEAD_TIMEOUT_SECONDS
            )
            parsed = _parse_request(raw_head)
        except (
            _BadRequestError,
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
            TimeoutError,
            ConnectionError,
        ):
            await self._reply(writer, 400)
            return None

        try:
            if parsed.port not in self._allowed_ports:
                raise UnsafeUrlError("Solo se permiten los puertos web estándar.")
            addresses = await self._resolve(parsed.host, parsed.port)
        except UnsafeUrlError:
            await self._reply(writer, 403)
            return None

        upstream = await self._connect(addresses, parsed.port)
        if upstream is None:
            await self._reply(writer, 502)
            return None

        if parsed.is_connect:
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        else:
            upstream[1].write(parsed.head)
        await writer.drain()
        await upstream[1].drain()
        return upstream

    async def _connect(self, addresses: list[str], port: int) -> Streams | None:
        # Siempre a las IP ya validadas: el nombre obligaría a resolver de nuevo.
        for address in addresses:
            try:
                return await asyncio.wait_for(
                    self._open_connection(address, port),
                    timeout=CONNECT_TIMEOUT_SECONDS,
                )
            except (OSError, TimeoutError):
                continue
        return None

    @staticmethod
    async def _reply(writer: asyncio.StreamWriter, status: int) -> None:
        reason = _REASONS[status]
        with contextlib.suppress(ConnectionError, OSError):
            writer.write(
                f"HTTP/1.1 {status} {reason}\r\nContent-Length: 0\r\n"
                "Connection: close\r\n\r\n".encode("ascii")
            )
            await writer.drain()

    @staticmethod
    async def _relay(
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        upstream_reader: asyncio.StreamReader,
        upstream_writer: asyncio.StreamWriter,
    ) -> None:
        pipes = {
            asyncio.ensure_future(_pipe(client_reader, upstream_writer)),
            asyncio.ensure_future(_pipe(upstream_reader, client_writer)),
        }
        try:
            await asyncio.wait(pipes, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for pipe in pipes:
                pipe.cancel()
            await asyncio.gather(*pipes, return_exceptions=True)


@asynccontextmanager
async def guarded_browser(playwright: Any) -> AsyncIterator[Any]:
    """Chromium que solo sale por el proxy de salida; ambos se cierran juntos."""
    async with EgressProxy() as proxy:
        # Playwright manda también el tráfico de loopback por el proxy salvo que se lo
        # excluya, así que ni `localhost` escapa de la validación.
        browser = await playwright.chromium.launch(
            headless=True, proxy={"server": proxy.url}
        )
        try:
            yield browser
        finally:
            await browser.close()
