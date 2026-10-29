"""Todo lo que conecta el navegador del scraper pasa por un proxy que valida.

La guarda de URLs resolvía el nombre una vez para decidir y Chromium lo volvía a
resolver después para conectar: un DNS que contesta distinto la segunda vez (DNS
rebinding) hacía que el navegador llegara a una IP interna que la guarda había aprobado
como pública. En el proxy el nombre se resuelve una sola vez, se valida y se conecta a
esa misma IP: no hay una segunda resolución que pueda cambiar.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.services.scraper import url_guard
from app.services.scraper.egress_proxy import EgressProxy, guarded_browser


class Upstream:
    """Un servidor de mentira en loopback: responde a un GET o repite lo recibido."""

    def __init__(self) -> None:
        self.port = 0
        self.received: list[bytes] = []
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        assert self._server is not None
        self._server.close()

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            data = await reader.read(65536)
            self.received.append(data)
            if data.startswith(b"GET "):
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Length: 4\r\n"
                    b"Connection: close\r\n\r\nhola"
                )
            else:
                writer.write(b"eco:" + data)
            await writer.drain()
        finally:
            writer.close()


@pytest.fixture
async def upstream() -> AsyncIterator[Upstream]:
    server = Upstream()
    await server.start()
    yield server
    await server.stop()


def _port_of(proxy: EgressProxy) -> int:
    return int(proxy.url.rsplit(":", 1)[1])


async def _ask(
    proxy: EgressProxy, request: bytes
) -> tuple[bytes, asyncio.StreamReader]:
    """Manda un pedido al proxy y devuelve la cabecera de la respuesta."""
    reader, writer = await asyncio.open_connection("127.0.0.1", _port_of(proxy))
    writer.write(request)
    await writer.drain()
    head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
    return head, reader


def _status(head: bytes) -> int:
    return int(head.split(b" ", 2)[1])


def _connect_to(upstream_port: int, recorded: list[tuple[str, int]]) -> Any:
    """Un `open_connection` que anota la IP pedida y conecta con el servidor local."""

    async def open_connection(host: str, port: int) -> Any:
        recorded.append((host, port))
        return await asyncio.open_connection("127.0.0.1", upstream_port)

    return open_connection


def _through(upstream: Upstream, recorded: list[tuple[str, int]]) -> EgressProxy:
    return EgressProxy(open_connection=_connect_to(upstream.port, recorded))


async def test_a_tunnel_reaches_the_destination_it_validated(
    upstream: Upstream,
) -> None:
    recorded: list[tuple[str, int]] = []
    async with _through(upstream, recorded) as proxy:
        reader, writer = await asyncio.open_connection("127.0.0.1", _port_of(proxy))
        writer.write(
            b"CONNECT sitio.example:443 HTTP/1.1\r\nHost: sitio.example:443\r\n\r\n"
        )
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
        assert _status(head) == 200

        writer.write(b"hola")
        await writer.drain()
        assert await asyncio.wait_for(reader.read(100), timeout=5) == b"eco:hola"
        writer.close()

    # Se conectó a la IP que el DNS devolvió y la guarda aprobó, no al nombre.
    assert recorded == [("93.184.216.34", 443)]


async def test_plain_http_is_forwarded_without_the_proxy_headers(
    upstream: Upstream,
) -> None:
    recorded: list[tuple[str, int]] = []
    async with _through(upstream, recorded) as proxy:
        head, reader = await _ask(
            proxy,
            b"GET http://sitio.example/empleo?id=7 HTTP/1.1\r\n"
            b"Host: sitio.example\r\n"
            b"Proxy-Connection: keep-alive\r\n"
            b"Accept: text/html\r\n\r\n",
        )
        body = await asyncio.wait_for(reader.read(100), timeout=5)

    assert _status(head) == 200
    assert body == b"hola"
    sent = upstream.received[0]
    assert sent.startswith(b"GET /empleo?id=7 HTTP/1.1\r\n")
    assert b"Host: sitio.example" in sent
    assert b"Accept: text/html" in sent
    assert b"Proxy-Connection" not in sent
    assert b"Connection: close" in sent
    assert recorded == [("93.184.216.34", 80)]


@pytest.mark.parametrize(
    "target",
    [
        "localhost:443",
        "intranet.local:443",
        "10.0.0.5:443",
        "169.254.169.254:80",
        "127.0.0.1:80",
        "[::1]:443",
        "[::ffff:10.0.0.5]:443",
        # Puertos que no son web: la guarda de URLs también los rechaza.
        "sitio.example:22",
        "sitio.example:6379",
        "sitio.example:8000",
    ],
)
async def test_internal_or_non_web_destinations_are_refused_before_connecting(
    target: str,
) -> None:
    recorded: list[tuple[str, int]] = []
    async with EgressProxy(open_connection=_connect_to(1, recorded)) as proxy:
        head, _ = await _ask(
            proxy, f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode()
        )

    assert _status(head) == 403
    assert recorded == []


async def test_a_name_that_resolves_to_a_private_address_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def resolve(_host: str, _port: int) -> list[str]:
        return ["10.1.2.3"]

    monkeypatch.setattr(url_guard, "_resolve", resolve)
    recorded: list[tuple[str, int]] = []
    async with EgressProxy(open_connection=_connect_to(1, recorded)) as proxy:
        head, _ = await _ask(
            proxy,
            b"CONNECT interno.example:443 HTTP/1.1\r\nHost: interno.example\r\n\r\n",
        )

    assert _status(head) == 403
    assert recorded == []


async def test_one_private_answer_among_public_ones_refuses_the_destination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def resolve(_host: str, _port: int) -> list[str]:
        return ["93.184.216.34", "127.0.0.1"]

    monkeypatch.setattr(url_guard, "_resolve", resolve)
    async with EgressProxy(open_connection=_connect_to(1, [])) as proxy:
        head, _ = await _ask(
            proxy, b"CONNECT mixto.example:443 HTTP/1.1\r\nHost: mixto.example\r\n\r\n"
        )

    assert _status(head) == 403


async def test_a_dns_that_changes_its_answer_cannot_redirect_the_connection(
    upstream: Upstream, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El ataque: pública cuando se valida, interna cuando se conecta.

    Se resuelve una vez por conexión y se conecta a lo validado. Un segundo pedido al
    mismo nombre, ya con la respuesta interna, se valida otra vez y se rechaza.
    """
    answers = [["93.184.216.34"], ["127.0.0.1"]]
    lookups: list[str] = []

    async def resolve(host: str, _port: int) -> list[str]:
        lookups.append(host)
        return answers[len(lookups) - 1]

    monkeypatch.setattr(url_guard, "_resolve", resolve)
    recorded: list[tuple[str, int]] = []
    request = b"CONNECT rebind.example:443 HTTP/1.1\r\nHost: rebind.example\r\n\r\n"
    async with _through(upstream, recorded) as proxy:
        first, _ = await _ask(proxy, request)
        second, _ = await _ask(proxy, request)

    assert (_status(first), _status(second)) == (200, 403)
    # Una sola consulta por conexión: entre validar y conectar no hay otra que cambie.
    assert lookups == ["rebind.example", "rebind.example"]
    assert recorded == [("93.184.216.34", 443)]


async def test_a_destination_that_cannot_be_reached_is_a_bad_gateway() -> None:
    async def refuse(_host: str, _port: int) -> Any:
        raise ConnectionRefusedError

    async with EgressProxy(open_connection=refuse) as proxy:
        head, _ = await _ask(
            proxy, b"CONNECT caido.example:443 HTTP/1.1\r\nHost: caido.example\r\n\r\n"
        )

    assert _status(head) == 502


@pytest.mark.parametrize(
    "request_line",
    [
        b"GET / HTTP/1.1",
        b"GET ftp://sitio.example/archivo HTTP/1.1",
        b"CONNECT sitio.example HTTP/1.1",
        b"CONNECT :443 HTTP/1.1",
        b"BASURA",
        b"GET http://sitio.example:abc/ HTTP/1.1",
    ],
)
async def test_requests_that_are_not_proxy_requests_are_bad_requests(
    request_line: bytes,
) -> None:
    async with EgressProxy(open_connection=_connect_to(1, [])) as proxy:
        head, _ = await _ask(proxy, request_line + b"\r\nHost: x\r\n\r\n")

    assert _status(head) == 400


async def test_closing_the_proxy_drops_the_tunnels_that_are_still_open() -> None:
    async def silent(_host: str, _port: int) -> Any:
        # Un destino que acepta y no dice nada: el túnel queda abierto.
        return await asyncio.open_connection("127.0.0.1", silent_server.port)

    silent_server = Upstream()
    await silent_server.start()
    try:
        async with EgressProxy(open_connection=silent) as proxy:
            reader, writer = await asyncio.open_connection("127.0.0.1", _port_of(proxy))
            writer.write(b"CONNECT sitio.example:443 HTTP/1.1\r\nHost: x\r\n\r\n")
            await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
        # Al salir del bloque, el túnel abierto ya no existe para quien estaba usándolo.
        assert await asyncio.wait_for(reader.read(100), timeout=5) == b""
        writer.close()
    finally:
        await silent_server.stop()


class _FakeBrowser:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _FakePlaywright:
    def __init__(self) -> None:
        self.launched: dict[str, Any] = {}
        self.browser = _FakeBrowser()
        self.chromium = self

    async def launch(self, **options: Any) -> _FakeBrowser:
        self.launched = options
        return self.browser


async def test_the_browser_goes_through_the_proxy_and_both_close_together() -> None:
    playwright = _FakePlaywright()

    async with guarded_browser(playwright) as browser:
        proxy_url = playwright.launched["proxy"]["server"]
        assert browser is playwright.browser
        assert playwright.launched["headless"] is True
        assert proxy_url.startswith("http://127.0.0.1:")
        # Mientras el navegador vive, el proxy acepta conexiones.
        _, writer = await asyncio.open_connection(
            "127.0.0.1", int(proxy_url.rsplit(":", 1)[1])
        )
        writer.close()

    assert playwright.browser.closed
    with pytest.raises(OSError):
        await asyncio.open_connection("127.0.0.1", int(proxy_url.rsplit(":", 1)[1]))
