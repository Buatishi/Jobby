import hashlib
import hmac
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services import email_service
from app.services.lemonsqueezy_service import handle_webhook_event
from tests.fakes import FakeRedis, FakeSupabase


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

    async def fake_handle(
        event_name: str,
        data: dict[str, Any],
        custom_data: dict[str, Any],
    ) -> None:
        handled.append((event_name, data, custom_data))

    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", secret)
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


def _signed_event(
    monkeypatch: pytest.MonkeyPatch, event_name: str = "subscription_created"
) -> tuple[bytes, dict[str, str]]:
    secret = "test-secret"
    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", secret)
    payload = {
        "meta": {"event_name": event_name, "custom_data": {"user_id": "user-1"}},
        "data": {"id": "sub_123", "attributes": {"status": "active"}},
    }
    raw_payload = json.dumps(payload).encode()
    return raw_payload, {"X-Signature": _signature(raw_payload, secret)}


def test_a_failed_event_answers_500_and_stays_unmarked_for_the_retry(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    raw_payload, headers = _signed_event(monkeypatch)

    async def failing_handle(*_args: object) -> None:
        raise RuntimeError("la base no respondió")

    monkeypatch.setattr("app.api.v1.webhooks.handle_webhook_event", failing_handle)

    response = client.post(
        "/api/v1/webhooks/lemonsqueezy", content=raw_payload, headers=headers
    )

    assert response.status_code == 500
    assert response.json()["code"] == "LEMONSQUEEZY_EVENT_FAILED"
    # Sin marca, el reintento de LemonSqueezy vuelve a procesarlo.
    assert fake_redis.values == {}


def test_a_processed_event_is_marked_and_a_repeat_is_skipped(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    raw_payload, headers = _signed_event(monkeypatch)
    handled: list[str] = []

    async def fake_handle(event_name: str, *_args: object) -> None:
        handled.append(event_name)

    monkeypatch.setattr("app.api.v1.webhooks.handle_webhook_event", fake_handle)

    first = client.post(
        "/api/v1/webhooks/lemonsqueezy", content=raw_payload, headers=headers
    )
    second = client.post(
        "/api/v1/webhooks/lemonsqueezy", content=raw_payload, headers=headers
    )

    assert first.status_code == second.status_code == 200
    assert handled == ["subscription_created"]
    assert list(fake_redis.values) == [
        "lemonsqueezy:webhook:subscription_created:sub_123"
    ]


def test_a_retry_after_a_failure_is_processed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    raw_payload, headers = _signed_event(monkeypatch)
    attempts: list[str] = []

    async def flaky_handle(event_name: str, *_args: object) -> None:
        attempts.append(event_name)
        if len(attempts) == 1:
            raise RuntimeError("falla pasajera")

    monkeypatch.setattr("app.api.v1.webhooks.handle_webhook_event", flaky_handle)

    failed = client.post(
        "/api/v1/webhooks/lemonsqueezy", content=raw_payload, headers=headers
    )
    retried = client.post(
        "/api/v1/webhooks/lemonsqueezy", content=raw_payload, headers=headers
    )

    assert (failed.status_code, retried.status_code) == (500, 200)
    assert len(attempts) == 2
    assert "lemonsqueezy:webhook:subscription_created:sub_123" in fake_redis.values


def _signed_update(
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    updated_at: str | None,
    subscription_id: str = "sub_123",
) -> tuple[bytes, dict[str, str]]:
    secret = "test-secret"
    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", secret)
    attributes: dict[str, Any] = {"status": status}
    if updated_at is not None:
        attributes["updated_at"] = updated_at
    payload = {
        "meta": {
            "event_name": "subscription_updated",
            "custom_data": {"user_id": "u1"},
        },
        "data": {"id": subscription_id, "attributes": attributes},
    }
    raw_payload = json.dumps(payload).encode()
    return raw_payload, {"X-Signature": _signature(raw_payload, secret)}


def test_two_updates_of_one_subscription_are_both_applied(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    """Cancelar y reanudar mandan dos `subscription_updated` con el mismo id.

    La marca era solo evento + id: el segundo se descartaba como repetido y quien había
    reanudado se quedaba en el plan gratuito. Ahora la marca incluye la versión del
    evento.
    """
    handled: list[str] = []

    async def fake_handle(
        _event: str, data: dict[str, Any], _custom: dict[str, Any]
    ) -> None:
        handled.append(data["attributes"]["status"])

    monkeypatch.setattr("app.api.v1.webhooks.handle_webhook_event", fake_handle)
    cancelled = _signed_update(monkeypatch, "cancelled", "2026-10-28T10:00:00.000000Z")
    resumed = _signed_update(monkeypatch, "active", "2026-10-28T12:30:00.000000Z")

    for raw_payload, headers in (cancelled, resumed):
        response = client.post(
            "/api/v1/webhooks/lemonsqueezy", content=raw_payload, headers=headers
        )
        assert response.status_code == 200

    assert handled == ["cancelled", "active"]


def test_the_same_update_delivered_twice_is_applied_once(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    handled: list[str] = []

    async def fake_handle(
        _event: str, data: dict[str, Any], _custom: dict[str, Any]
    ) -> None:
        handled.append(data["attributes"]["status"])

    monkeypatch.setattr("app.api.v1.webhooks.handle_webhook_event", fake_handle)
    raw_payload, headers = _signed_update(
        monkeypatch, "cancelled", "2026-10-28T10:00:00.000000Z"
    )

    for _ in range(2):
        client.post(
            "/api/v1/webhooks/lemonsqueezy", content=raw_payload, headers=headers
        )

    assert handled == ["cancelled"]


def test_a_non_ascii_signature_is_just_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`compare_digest` con texto no ASCII lanzaba TypeError y la API respondía 500."""
    from app.services.lemonsqueezy_service import verify_webhook_signature

    monkeypatch.setattr(settings, "lemonsqueezy_webhook_secret", "test-secret")

    assert verify_webhook_signature(b"{}", "firma-inválida-é") is False


def _post(client: TestClient, signed: tuple[bytes, dict[str, str]]) -> int:
    raw_payload, headers = signed
    return client.post(
        "/api/v1/webhooks/lemonsqueezy", content=raw_payload, headers=headers
    ).status_code


def _record_statuses(
    monkeypatch: pytest.MonkeyPatch, fail_first_cancel: bool = False
) -> list[str]:
    handled: list[str] = []
    failures = {"left": 1 if fail_first_cancel else 0}

    async def fake_handle(
        _event: str, data: dict[str, Any], _custom: dict[str, Any]
    ) -> None:
        status = data["attributes"]["status"]
        if status == "cancelled" and failures["left"]:
            failures["left"] -= 1
            raise RuntimeError("la base no respondió")
        handled.append(status)

    monkeypatch.setattr("app.api.v1.webhooks.handle_webhook_event", fake_handle)
    return handled


def test_a_late_retry_of_an_older_update_does_not_undo_a_newer_one(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    """Cancelar falla, se reanuda, y recién después LemonSqueezy reintenta el cancelar.

    Aplicar ese reintento dejaba cancelada a una persona que ya había reanudado.
    """
    handled = _record_statuses(monkeypatch, fail_first_cancel=True)
    cancel = _signed_update(monkeypatch, "cancelled", "2026-10-29T10:00:00.000000Z")
    resume = _signed_update(monkeypatch, "active", "2026-10-29T10:02:00.000000Z")

    codes = [_post(client, cancel), _post(client, resume), _post(client, cancel)]

    assert codes == [500, 200, 200]
    assert handled == ["active"]


def test_the_newest_version_applied_is_remembered_with_an_expiry(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    _record_statuses(monkeypatch)
    older = _signed_update(monkeypatch, "cancelled", "2026-10-29T10:00:00.000000Z")
    newer = _signed_update(monkeypatch, "active", "2026-10-29T10:02:00.000000Z")

    _post(client, older)
    _post(client, newer)

    key = "lemonsqueezy:webhook:latest:subscription_updated:sub_123"
    assert fake_redis.values[key] == "2026-10-29T10:02:00.000000Z"
    assert fake_redis.ttls[key] > 0


def test_updates_of_different_subscriptions_are_not_ordered_against_each_other(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    handled = _record_statuses(monkeypatch)
    newer = _signed_update(
        monkeypatch, "active", "2026-10-29T10:02:00.000000Z", "sub_a"
    )
    older = _signed_update(
        monkeypatch, "cancelled", "2026-10-29T10:00:00.000000Z", "sub_b"
    )

    _post(client, newer)
    _post(client, older)

    assert handled == ["active", "cancelled"]


def test_versions_that_are_not_dates_are_not_compared(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    handled = _record_statuses(monkeypatch)
    first = _signed_update(monkeypatch, "active", "v2")
    second = _signed_update(monkeypatch, "cancelled", "v1")

    _post(client, first)
    _post(client, second)

    assert handled == ["active", "cancelled"]


def test_a_redis_failure_checking_the_order_still_applies_the_update(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    handled = _record_statuses(monkeypatch)

    async def broken(*_args: object) -> None:
        raise ConnectionError("Redis no responde")

    monkeypatch.setattr("app.api.v1.webhooks._is_stale", broken)
    signed = _signed_update(monkeypatch, "active", "2026-10-29T10:02:00.000000Z")

    assert _post(client, signed) == 200
    assert handled == ["active"]

