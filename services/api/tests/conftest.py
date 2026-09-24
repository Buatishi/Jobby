from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis

from app.main import app
from tests.fakes import FakeRedis


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Los tests no dependen de DNS real: todo host resuelve a una IP pública."""

    async def fake_resolve(_host: str, _port: int) -> list[str]:
        return ["93.184.216.34"]

    monkeypatch.setattr("app.services.scraper.url_guard._resolve", fake_resolve)


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    """Ningún test se conecta a un Redis real: cada uno recibe uno vacío en memoria.

    Antes, un test que llegaba al límite de uso intentaba conectarse al REDIS_URL real y
    fallaba con un error de conexión en vez de una aserción clara.
    """
    redis = FakeRedis()
    monkeypatch.setattr(Redis, "from_url", staticmethod(lambda *_a, **_k: redis))
    return redis
