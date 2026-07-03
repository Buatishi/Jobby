import hashlib
import hmac
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services import email_service
from app.services.lemonsqueezy_service import handle_webhook_event
from tests.fakes import FakeSupabase


def _signature(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_lemonsqueezy_webhook_valid_signature(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handled: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    secret = "test-secret"
    payload = {
        "meta": {
            "event_name": "subscription_created",
            "custom_data": {"user_id": "user-1"},
        },
        "data": {"id": "sub_123", "attributes": {"status": "active"}},
    }
    raw_payload = json.dumps(payload).encode()

    async def fake_processed(_event_key: str) -> bool:
        return False

    async def fake_handle(
        event_name: str,
        data: dict[str, Any],
        custom_data: dict[str, Any],
    ) -> None:
        handled.append((event_name, data, custom_data))

    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", secret)
    monkeypatch.setattr("app.api.v1.webhooks._already_processed", fake_processed)
    monkeypatch.setattr("app.api.v1.webhooks.handle_webhook_event", fake_handle)

    response = client.post(
        "/api/v1/webhooks/lemonsqueezy",
        content=raw_payload,
        headers={"X-Signature": _signature(raw_payload, secret)},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert handled == [
        ("subscription_created", payload["data"], {"user_id": "user-1"})
    ]


def test_lemonsqueezy_webhook_invalid_signature(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", "test-secret")

    response = client.post(
        "/api/v1/webhooks/lemonsqueezy",
        content=b'{"id":"evt_123"}',
        headers={"X-Signature": "bad"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "LEMONSQUEEZY_SIGNATURE_INVALID"


@pytest.mark.asyncio
async def test_payment_failed_sends_email_and_downgrades(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["users"][0]["tier"] = "premium"
    sent: list[tuple[str, int]] = []

    def fake_payment_failed(user: dict[str, object], attempt_number: int) -> None:
        sent.append((str(user["email"]), attempt_number))

    monkeypatch.setattr(email_service, "send_payment_failed", fake_payment_failed)

    await handle_webhook_event(
        "subscription_payment_failed",
        {
            "id": "sub_123",
            "attributes": {
                "customer_id": "cus_123",
                "attempt_count": 3,
            },
        },
        {"user_id": "user-1"},
        db=fake_supabase,
    )

    user = fake_supabase.tables["users"][0]
    assert user["tier"] == "free"
    assert user["payment_provider"] == "lemonsqueezy"
    assert user["subscription_status"] == "payment_failed"
    assert sent == [("person@example.com", 3)]
