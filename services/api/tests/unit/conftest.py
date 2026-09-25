"""Las pruebas unitarias no salen a la red.

Con el `.env` local apuntando a producción, una prueba que olvidaba simular un servicio
le pegaba de verdad: así se encontró que `test_invalid_token_returns_401` consultaba el
Supabase Auth de producción en cada corrida. Acá los transportes reales de httpx fallan
y la prueba queda en rojo aunque el código atrape el error. El cliente de pruebas de
FastAPI y los transportes simulados no pasan por ellos. Las pruebas de integración
(`tests/integration`) sí usan la red y no cargan este archivo.
"""

from collections.abc import Iterator

import httpx
import pytest


class UnitTestNetworkError(RuntimeError):
    pass


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    attempts: list[str] = []

    def refuse(_transport: object, request: httpx.Request) -> httpx.Response:
        attempt = f"{request.method} {request.url.host}{request.url.path}"
        attempts.append(attempt)
        raise UnitTestNetworkError(
            f"Una prueba unitaria intentó salir a la red: {attempt}"
        )

    async def refuse_async(transport: object, request: httpx.Request) -> httpx.Response:
        return refuse(transport, request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", refuse_async)
    yield
    assert not attempts, f"Las pruebas unitarias no usan la red; se intentó: {attempts}"
