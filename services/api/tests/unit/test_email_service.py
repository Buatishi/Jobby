"""Los correos transaccionales no pueden llevar HTML que elige quien se registró."""

from typing import Any

import pytest

from app.services import email_service


class FakeEmails:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def send(self, payload: dict[str, Any]) -> None:
        self.sent.append(payload)


class FakeResend:
    api_key = ""

    def __init__(self) -> None:
        self.Emails = FakeEmails()


@pytest.fixture
def resend(monkeypatch: pytest.MonkeyPatch) -> FakeResend:
    fake = FakeResend()
    monkeypatch.setattr(email_service.settings, "resend_api_key", "re_test")
    monkeypatch.setattr(email_service, "_resend_client", lambda: fake)
    return fake


def test_the_payment_failed_email_escapes_the_name(resend: FakeResend) -> None:
    """`full_name` sale de los metadatos del alta, que cualquiera puede escribir."""
    email_service.send_payment_failed(
        {
            "email": "person@example.test",
            "full_name": '<a href="https://example.invalid/pay">Pagá acá</a>',
        },
        2,
    )

    (payload,) = resend.Emails.sent
    assert payload["to"] == ["person@example.test"]
    assert "<a href" not in payload["html"]
    assert "&lt;a href=" in payload["html"]
    assert "Intento #2" in payload["html"]


def test_a_plain_name_is_kept(resend: FakeResend) -> None:
    email_service.send_payment_failed(
        {"email": "person@example.test", "full_name": "Ana Pérez"}, 1
    )

    assert "Ana Pérez, no pudimos procesar tu pago" in resend.Emails.sent[0]["html"]
