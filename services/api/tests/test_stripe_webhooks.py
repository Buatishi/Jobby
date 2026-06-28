import pytest
from fastapi.testclient import TestClient

from app.api.v1 import webhooks


def test_stripe_webhook_valid_signature(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handled: list[dict[str, object]] = []
    event = {
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "customer": "cus_123",
                "status": "active",
                "metadata": {"user_id": "user-1"},
            }
        },
    }

    def fake_construct_event(
        _payload: bytes,
        signature: str,
        _secret: str,
    ) -> dict[str, object]:
        assert signature == "valid"
        return event

    async def fake_handle_webhook(payload: dict[str, object]) -> None:
        handled.append(payload)

    monkeypatch.setattr(
        webhooks.stripe.Webhook,
        "construct_event",
        fake_construct_event,
    )
    monkeypatch.setattr(webhooks, "handle_webhook", fake_handle_webhook)

    response = client.post(
        "/api/v1/webhooks/stripe",
        content=b'{"id":"evt_123"}',
        headers={"stripe-signature": "valid"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert handled == [event]


def test_stripe_webhook_invalid_signature(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_construct_event(
        _payload: bytes,
        _signature: str,
        _secret: str,
    ) -> dict[str, object]:
        raise webhooks.stripe.error.SignatureVerificationError(
            message="invalid",
            sig_header="bad",
        )

    monkeypatch.setattr(
        webhooks.stripe.Webhook,
        "construct_event",
        fake_construct_event,
    )

    response = client.post(
        "/api/v1/webhooks/stripe",
        content=b'{"id":"evt_123"}',
        headers={"stripe-signature": "bad"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "STRIPE_SIGNATURE_INVALID"
