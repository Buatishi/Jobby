import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.lemonsqueezy_service import (
    CheckoutCreationError,
    create_checkout_url,
)

CHECKOUT_URL = "https://jobby.lemonsqueezy.com/checkout/custom/abc-123?signature=x"


@pytest.fixture(autouse=True)
def _lemon_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "lemonsqueezy_api_key", "test-api-key")
    monkeypatch.setattr(settings, "lemonsqueezy_store_id", "11111")
    monkeypatch.setattr(settings, "lemonsqueezy_premium_variant_id", "22222")


def _client(handler) -> httpx.AsyncClient:  # type: ignore[no-untyped-def]
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _created(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        201, json={"data": {"attributes": {"url": CHECKOUT_URL}}}
    )


async def test_asks_lemon_for_a_checkout_and_returns_its_url() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _created(request)

    url = await create_checkout_url("user-1", "person@example.com", _client(handler))

    assert url == CHECKOUT_URL
    request = seen[0]
    assert str(request.url) == "https://api.lemonsqueezy.com/v1/checkouts"
    assert request.headers["authorization"] == "Bearer test-api-key"
    body = json.loads(request.content)["data"]
    assert body["relationships"]["store"]["data"]["id"] == "11111"
    assert body["relationships"]["variant"]["data"]["id"] == "22222"
    # El user_id vuelve en el webhook: es lo que liga el pago con la persona.
    assert body["attributes"]["checkout_data"] == {
        "email": "person@example.com",
        "custom": {"user_id": "user-1"},
    }


@pytest.mark.parametrize("status_code", [401, 404, 422, 500])
async def test_a_lemon_error_is_not_turned_into_a_link(status_code: int) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"errors": [{"detail": "x"}]})

    with pytest.raises(CheckoutCreationError):
        await create_checkout_url("user-1", "person@example.com", _client(handler))


@pytest.mark.parametrize(
    "body",
    [{}, {"data": {"attributes": {}}}, {"data": {"attributes": {"url": "http://x"}}}],
)
async def test_a_reply_without_a_usable_url_is_rejected(body: dict) -> None:  # type: ignore[type-arg]
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json=body)

    with pytest.raises(CheckoutCreationError):
        await create_checkout_url("user-1", "person@example.com", _client(handler))


async def test_lemon_being_unreachable_is_a_checkout_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(CheckoutCreationError):
        await create_checkout_url("user-1", "person@example.com", _client(handler))


@pytest.mark.parametrize(
    "setting",
    [
        "lemonsqueezy_api_key",
        "lemonsqueezy_store_id",
        "lemonsqueezy_premium_variant_id",
    ],
)
async def test_missing_configuration_fails_before_calling_lemon(
    monkeypatch: pytest.MonkeyPatch, setting: str
) -> None:
    monkeypatch.setattr(settings, setting, "")

    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("Lemon must not be called without configuration")

    with pytest.raises(CheckoutCreationError):
        await create_checkout_url("user-1", "person@example.com", _client(handler))


async def test_an_email_is_required() -> None:
    with pytest.raises(CheckoutCreationError):
        await create_checkout_url("user-1", "", _client(_created))


async def _person() -> CurrentUser:
    return CurrentUser(id="user-1", supabase_uid="auth-1", email="p@example.com")


def test_endpoint_returns_the_checkout_url(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_create(user_id: str, email: str) -> str:
        assert (user_id, email) == ("user-1", "p@example.com")
        return CHECKOUT_URL

    monkeypatch.setattr("app.api.v1.billing.create_checkout_url", fake_create)
    app.dependency_overrides[get_current_user] = _person

    response = client.post("/api/v1/billing/checkout")

    assert response.status_code == 200
    assert response.json() == {"checkout_url": CHECKOUT_URL}


def test_endpoint_answers_502_with_a_clear_message_when_lemon_fails(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def failing(_user_id: str, _email: str) -> str:
        raise CheckoutCreationError("Lemon Squeezy answered 404 creating the checkout.")

    monkeypatch.setattr("app.api.v1.billing.create_checkout_url", failing)
    app.dependency_overrides[get_current_user] = _person

    response = client.post("/api/v1/billing/checkout")

    assert response.status_code == 502
    assert response.json()["code"] == "BILLING_CHECKOUT_FAILED"
    assert response.json()["error"] == "Los pagos todavía no están disponibles"
    # El motivo queda en los registros para poder diagnosticar la configuración.
    assert "Lemon Squeezy answered 404" in caplog.text
    assert "p@example.com" not in caplog.text
