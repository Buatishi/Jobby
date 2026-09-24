from typing import Any, Protocol, cast

from app.config import settings

SENDER = "noreply@jobmatch.ai"


class ResendEmailsClient(Protocol):
    def send(self, payload: dict[str, Any]) -> Any: ...


class ResendClient(Protocol):
    Emails: ResendEmailsClient
    api_key: str


def _resend_client() -> ResendClient:
    import resend

    resend.api_key = settings.resend_api_key
    return cast(ResendClient, resend)


def _recipient(user: dict[str, Any]) -> str:
    email = user.get("email")
    if not isinstance(email, str) or not email:
        raise ValueError("User does not have an email address.")
    return email


def _name(user: dict[str, Any]) -> str:
    full_name = user.get("full_name")
    if isinstance(full_name, str) and full_name.strip():
        return full_name.strip()
    return "hola"


def _send(user: dict[str, Any], subject: str, html: str) -> None:
    if not settings.resend_api_key:
        return
    _resend_client().Emails.send(
        {
            "from": SENDER,
            "to": [_recipient(user)],
            "subject": subject,
            "html": html,
        }
    )


def send_payment_failed(user: dict[str, Any], attempt_number: int) -> None:
    _send(
        user,
        "No pudimos procesar tu pago",
        (
            f"<p>{_name(user)}, no pudimos procesar tu pago de Premium.</p>"
            f"<p>Intento #{attempt_number}. Actualiza tu metodo de pago para "
            "evitar la baja del plan.</p>"
        ),
    )
