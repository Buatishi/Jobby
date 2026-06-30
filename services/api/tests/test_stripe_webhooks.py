import pytest
from fastapi.testclient import TestClient

from app.api.v1 import webhooks
from app.services import email_service
from app.services.stripe_service import handle_webhook
from tests.fakes import FakeSupabase


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


@pytest.mark.asyncio
async def test_payment_failed_sends_email_and_downgrades(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["users"][0]["tier"] = "premium"
    fake_supabase.tables["users"][0]["stripe_customer_id"] = "cus_123"
    sent: list[tuple[str, int | None]] = []

    def fake_payment_failed(user: dict[str, object], attempt_number: int) -> None:
        sent.append((str(user["email"]), attempt_number))

    def fake_downgrade(user: dict[str, object]) -> None:
        sent.append((str(user["email"]), None))

    monkeypatch.setattr(email_service, "send_payment_failed", fake_payment_failed)
    monkeypatch.setattr(
        email_service,
        "send_downgrade_notification",
        fake_downgrade,
    )

    await handle_webhook(
        {
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "customer": "cus_123",
                    "attempt_count": 2,
                }
            },
        },
        db=fake_supabase,
    )

    assert fake_supabase.tables["users"][0]["tier"] == "free"
    assert sent == [("person@example.com", 2), ("person@example.com", None)]
