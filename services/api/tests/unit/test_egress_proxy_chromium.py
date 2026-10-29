"""El proxy de salida con un Chromium de verdad.

Las pruebas de `test_egress_proxy.py` usan sockets; estas comprueban lo que depende del
navegador: que Playwright mande también el tráfico de loopback por el proxy (si no, el
navegador llegaría a un servicio interno sin pasar por la validación) y que Chromium
confíe en el proxy para resolver el nombre. Se saltan si Chromium no está instalado
(`playwright install chromium`), como en la imagen de la API.
"""

import threading
from collections.abc import AsyncIterator, Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from app.services.scraper.egress_proxy import EgressProxy

MARKER = "MARCADOR-DEL-SERVICIO-INTERNO"


class _Internal:
    """Un servicio que solo debería verse desde adentro: anota quién lo visita."""

    def __init__(self) -> None:
        self.hits: list[str] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                outer.hits.append(f"{self.headers.get('Host')} {self.path}")
                body = f"<html><body>{MARKER}</body></html>".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args: Any) -> None:
                return None

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self.port: int = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture
def internal() -> Iterator[_Internal]:
    service = _Internal()
    yield service
    service.stop()


@pytest.fixture
async def chromium() -> AsyncIterator[Any]:
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        yield playwright.chromium


async def _launch(chromium: Any, proxy: EgressProxy) -> Any:
    try:
        return await chromium.launch(headless=True, proxy={"server": proxy.url})
    except Exception as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Chromium no está instalado")
        raise


async def _body_text(browser: Any, url: str) -> str:
    page = await browser.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15_000)
        return str(await page.locator("body").inner_text(timeout=5_000)).strip()
    except Exception:
        return ""  # El proxy cortó el túnel: no hay página.
    finally:
        await page.close()


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "[::1]"])
async def test_the_browser_cannot_reach_an_internal_service_through_the_proxy(
    chromium: Any, internal: _Internal, host: str
) -> None:
    async with EgressProxy(allowed_ports=frozenset({internal.port})) as proxy:
        browser = await _launch(chromium, proxy)
        try:
            text = await _body_text(browser, f"http://{host}:{internal.port}/")
        finally:
            await browser.close()

    assert MARKER not in text
    # Si Chromium saltara el proxy con el tráfico de loopback, vería la visita.
    assert internal.hits == []


async def test_the_proxy_resolves_the_name_so_the_browser_needs_no_dns_of_its_own(
    chromium: Any, internal: _Internal
) -> None:
    async def resolve(_host: str, _port: int) -> list[str]:
        return ["127.0.0.1"]  # Para este test, el servidor local hace de IP pública.

    # `sitio.test` no existe en ningún DNS: si carga, fue el proxy quien lo resolvió.
    async with EgressProxy(
        resolve=resolve, allowed_ports=frozenset({internal.port})
    ) as proxy:
        browser = await _launch(chromium, proxy)
        try:
            text = await _body_text(browser, f"http://sitio.test:{internal.port}/empleo")
        finally:
            await browser.close()

    assert MARKER in text
    assert internal.hits == [f"sitio.test:{internal.port} /empleo"]
