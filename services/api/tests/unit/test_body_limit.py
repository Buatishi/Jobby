"""Un cuerpo enorme no se lee entero: se corta antes de autenticar y de validar.

El webhook de LemonSqueezy hacía `await request.body()` antes de mirar la firma, y la
API no tenía ningún tope: una petición sin sesión podía hacer que el proceso (de 512 MB,
que además corre las tareas locales) cargara cientos de MB. Los cuerpos reales son
chicos (el más grande, un texto de puesto, pesa unos cientos de KB), así que el tope es
de 2 MiB.
"""

from collections.abc import Iterator

from fastapi.testclient import TestClient

WEBHOOK = "/api/v1/webhooks/lemonsqueezy"
LIMIT = 2 * 1024 * 1024


def test_a_declared_oversized_body_is_refused_before_it_is_read(
    client: TestClient,
) -> None:
    response = client.post(WEBHOOK, content=b"x" * (LIMIT + 1))

    assert response.status_code == 413
    body = response.json()
    assert body["code"] == "REQUEST_TOO_LARGE"
    assert set(body) == {"error", "code", "details"}


def test_a_chunked_body_without_content_length_is_also_cut(
    client: TestClient,
) -> None:
    def chunks() -> Iterator[bytes]:
        for _ in range(3):
            yield b"x" * (1024 * 1024)

    response = client.post(WEBHOOK, content=chunks())

    assert response.status_code == 413
    assert response.json()["code"] == "REQUEST_TOO_LARGE"


def test_bodies_up_to_the_limit_still_reach_the_route(client: TestClient) -> None:
    # Llegan a la ruta, que los rechaza por la firma que falta: no por el tamaño.
    for size in (300 * 1024, LIMIT):
        response = client.post(WEBHOOK, content=b"x" * size)
        assert response.status_code == 400
        assert response.json()["code"] == "LEMONSQUEEZY_SIGNATURE_MISSING"
