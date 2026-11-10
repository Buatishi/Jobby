"""Tope por IP a los pedidos sin sesión (Decisión 46).

La API en Render tiene su propia dirección pública y limitaba solo por usuario con
sesión: cualquiera podía mandarle pedidos sin sesión sin freno. Solo tres de sus 41
rutas responden sin sesión (`/health`, `/api/v1/health` y el aviso de pago de
LemonSqueezy); el resto contesta 401, así que quien insiste sin sesión es un escáner o
un bucle.

El tope cuenta únicamente pedidos SIN encabezado `Authorization`: nunca alcanza a una
persona con sesión, aunque la IP se identificara mal. Sin una IP usable (o si Redis
falla) no limita.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.config import settings
from app.core import ip_rate_limit
from app.core.ip_rate_limit import IP_LIMIT_PER_MINUTE, client_ip
from tests.fakes import FakeRedis

# Una ruta que existe y exige sesión: sin sesión contesta 401.
PROTECTED = "/api/v1/profiles/me"
SCANNER = {"X-Forwarded-For": "8.8.8.8"}


def _request(headers: dict[str, str], client_host: str | None = "10.0.0.5") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (client_host, 1234) if client_host else None,
    }
    return Request(scope)


# --- qué IP se usa
# ---------------------------------------------------------------------


def test_the_ip_is_the_first_entry_of_x_forwarded_for() -> None:
    request = _request({"X-Forwarded-For": " 8.8.8.8 , 70.41.3.18, 150.172.238.178"})

    assert client_ip(request) == "8.8.8.8"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Forwarded-For": ""},
        {"X-Forwarded-For": "no-es-una-ip"},
        {"X-Forwarded-For": "999.1.1.1"},
        # Una dirección interna es la de un proxy de Render, no la de una persona:
        # usarla
        # juntaría a todos en el mismo contador.
        {"X-Forwarded-For": "10.228.27.128"},
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Forwarded-For": "192.168.1.20"},
        {"X-Forwarded-For": "100.64.0.9"},
        {"X-Forwarded-For": "203.0.113.7"},
    ],
)
def test_without_a_usable_ip_there_is_no_ip(headers: dict[str, str]) -> None:
    assert client_ip(_request(headers)) is None


def test_the_connection_address_is_never_used() -> None:
    """En Render es la del balanceador: todas las visitas compartirían el contador."""
    assert client_ip(_request({}, client_host="1.1.1.1")) is None


def test_an_ipv6_address_counts_as_its_64_bit_network() -> None:
    """Quien tiene IPv6 recibe un /64 entero: contar por dirección dejaría rotarla."""
    first = client_ip(_request({"X-Forwarded-For": "2a00:1450:4001:81b::1"}))
    second = client_ip(_request({"X-Forwarded-For": "2a00:1450:4001:81b:ffff::9"}))
    other = client_ip(_request({"X-Forwarded-For": "2a00:1450:4001:81c::1"}))

    assert first == second
    assert first != other


# --- el tope
# ---------------------------------------------------------------------------


def test_the_limit_is_far_above_any_real_use_without_a_session() -> None:
    assert IP_LIMIT_PER_MINUTE == 60


def test_the_request_after_the_limit_answers_429_in_the_standard_error_shape(
    client: TestClient,
) -> None:
    statuses = [
        client.get(PROTECTED, headers=SCANNER).status_code
        for _ in range(IP_LIMIT_PER_MINUTE)
    ]
    blocked = client.get(PROTECTED, headers=SCANNER)

    assert set(statuses) == {401}
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "IP_RATE_LIMIT_EXCEEDED"
    assert blocked.json()["error"]
    assert 1 <= blocked.json()["details"]["retry_after_seconds"] <= 60
    assert blocked.headers["retry-after"] == str(
        blocked.json()["details"]["retry_after_seconds"]
    )


def test_each_ip_has_its_own_count(client: TestClient) -> None:
    for _ in range(IP_LIMIT_PER_MINUTE + 5):
        client.get(PROTECTED, headers=SCANNER)

    other = client.get(PROTECTED, headers={"X-Forwarded-For": "1.1.1.1"})

    assert other.status_code == 401


def test_the_count_starts_again_in_the_next_minute(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ip_rate_limit, "_now", lambda: 1_000_000.0)
    for _ in range(IP_LIMIT_PER_MINUTE + 5):
        client.get(PROTECTED, headers=SCANNER)
    assert client.get(PROTECTED, headers=SCANNER).status_code == 429

    monkeypatch.setattr(ip_rate_limit, "_now", lambda: 1_000_061.0)

    assert client.get(PROTECTED, headers=SCANNER).status_code == 401


def test_the_counter_expires_by_itself(
    client: TestClient, fake_redis: FakeRedis
) -> None:
    client.get(PROTECTED, headers=SCANNER)

    keys = [key for key in fake_redis.values if key.startswith("rate:ip:")]
    assert len(keys) == 1
    assert 60 < fake_redis.ttls[keys[0]] <= 180


# --- a quién nunca alcanza
# -------------------------------------------------------------


def test_a_request_with_a_session_header_is_never_counted(
    client: TestClient, fake_redis: FakeRedis
) -> None:
    headers = {**SCANNER, "Authorization": "Bearer cualquier-cosa"}

    statuses = {
        client.get(PROTECTED, headers=headers).status_code
        for _ in range(IP_LIMIT_PER_MINUTE * 3)
    }

    assert 429 not in statuses
    assert not [key for key in fake_redis.values if key.startswith("rate:ip:")]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/health"),
        ("GET", "/api/v1/health"),
        ("POST", "/api/v1/webhooks/lemonsqueezy"),
    ],
)
def test_the_routes_that_answer_without_a_session_are_never_limited(
    client: TestClient, fake_redis: FakeRedis, method: str, path: str
) -> None:
    """Render pide /health todo el día; LemonSqueezy avisa los pagos por el webhook y
    no puede quedar con un 429."""
    statuses = {
        client.request(method, path, headers=SCANNER).status_code
        for _ in range(IP_LIMIT_PER_MINUTE * 2)
    }

    assert 429 not in statuses
    assert not [key for key in fake_redis.values if key.startswith("rate:ip:")]


def test_the_preflight_of_a_browser_is_never_limited(client: TestClient) -> None:
    headers = {
        **SCANNER,
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    }

    statuses = {
        client.options(PROTECTED, headers=headers).status_code
        for _ in range(IP_LIMIT_PER_MINUTE * 2)
    }

    assert 429 not in statuses


def test_without_a_usable_ip_nothing_is_limited(client: TestClient) -> None:
    statuses = {
        client.get(PROTECTED).status_code for _ in range(IP_LIMIT_PER_MINUTE * 2)
    }

    assert statuses == {401}


def test_it_can_be_switched_off_without_touching_the_code(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ip_rate_limit_enabled", False)

    statuses = {
        client.get(PROTECTED, headers=SCANNER).status_code
        for _ in range(IP_LIMIT_PER_MINUTE * 2)
    }

    assert statuses == {401}


def test_if_redis_fails_the_request_goes_through(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BrokenRedis:
        async def incr(self, _key: str) -> int:
            raise ConnectionError("Redis no responde")

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(
        ip_rate_limit.Redis, "from_url", staticmethod(lambda *_a, **_k: BrokenRedis())
    )

    assert client.get(PROTECTED, headers=SCANNER).status_code == 401


# --- cómo contesta el 429
# --------------------------------------------------------------


def test_the_429_keeps_the_cors_and_security_headers(client: TestClient) -> None:
    headers = {**SCANNER, "Origin": "http://localhost:3000"}
    for _ in range(IP_LIMIT_PER_MINUTE):
        client.get(PROTECTED, headers=headers)

    blocked = client.get(PROTECTED, headers=headers)

    assert blocked.status_code == 429
    # Sin CORS el navegador mostraría un error de red en vez del mensaje.
    assert blocked.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert blocked.headers["x-content-type-options"] == "nosniff"
