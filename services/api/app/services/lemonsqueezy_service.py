import hashlib
import hmac
from typing import Any

import httpx

from app.config import settings
from app.database import get_supabase_client
from app.services import email_service
from app.services.account_deletion import capture_exception


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


LEMONSQUEEZY_CHECKOUTS_URL = "https://api.lemonsqueezy.com/v1/checkouts"
_JSON_API = "application/vnd.api+json"


class CheckoutCreationError(RuntimeError):
    """Lemon Squeezy no devolvió un enlace de pago usable (configuración o servicio)."""


def _error_sources(response: httpx.Response) -> str:
    """Qué campo rechazó Lemon, por ejemplo la tienda o la variante.

    Solo `title` y `source.pointer` de cada error: el `detail` puede repetir valores
    enviados (el email), así que no se registra.
    """
    try:
        errors = response.json().get("errors", [])
        found = [
            f"{error.get('title')} at {error.get('source', {}).get('pointer')}"
            for error in errors[:3]
            if isinstance(error, dict)
        ]
    except (ValueError, AttributeError):
        return ""
    return f" ({'; '.join(found)})"[:300] if found else ""


async def create_checkout_url(
    user_id: str,
    user_email: str,
    client: httpx.AsyncClient | None = None,
) -> str:
    """Pide a la API de Lemon Squeezy un checkout para esta persona y devuelve su URL.

    Armar el enlace a mano (subdominio de la tienda + código de compra) dejaba a la
    persona en una página de error de Lemon si algún identificador no coincidía. Con la
    API, una configuración incorrecta falla acá, donde la web puede avisar con claridad.
    El `user_id` viaja como dato propio del checkout y vuelve en el webhook.
    """
    if not settings.lemonsqueezy_api_key:
        raise CheckoutCreationError("Missing Lemon Squeezy API key.")
    if not settings.lemonsqueezy_store_id:
        raise CheckoutCreationError("Missing Lemon Squeezy store id.")
    if not settings.lemonsqueezy_premium_variant_id:
        raise CheckoutCreationError("Missing Lemon Squeezy premium variant id.")
    if not user_email:
        raise CheckoutCreationError("User email is required to create checkout.")

    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": user_email,
                    "custom": {"user_id": user_id},
                }
            },
            "relationships": {
                "store": {
                    "data": {"type": "stores", "id": settings.lemonsqueezy_store_id}
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": settings.lemonsqueezy_premium_variant_id,
                    }
                },
            },
        }
    }
    headers = {
        "Accept": _JSON_API,
        "Content-Type": _JSON_API,
        "Authorization": f"Bearer {settings.lemonsqueezy_api_key}",
    }

    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=10.0)
    try:
        response = await http.post(
            LEMONSQUEEZY_CHECKOUTS_URL, json=payload, headers=headers
        )
    except httpx.HTTPError as exc:
        raise CheckoutCreationError("Lemon Squeezy is not reachable.") from exc
    finally:
        if owns_client:
            await http.aclose()

    if response.status_code != httpx.codes.CREATED:
        raise CheckoutCreationError(
            f"Lemon Squeezy answered {response.status_code} creating the checkout"
            f"{_error_sources(response)}."
        )

    try:
        url = response.json()["data"]["attributes"]["url"]
    except (ValueError, KeyError, TypeError) as exc:
        raise CheckoutCreationError("Lemon Squeezy sent no checkout URL.") from exc
    if not isinstance(url, str) or not url.startswith("https://"):
        raise CheckoutCreationError("Lemon Squeezy sent an invalid checkout URL.")
    return url


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    if not settings.lemonsqueezy_webhook_secret or not signature:
        return False

    digest = hmac.new(
        settings.lemonsqueezy_webhook_secret.encode(),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


def _user_id(custom_data: dict[str, Any]) -> str | None:
    value = custom_data.get("user_id")
    return str(value) if value else None


def _str_or_none(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _period_end(attributes: dict[str, Any]) -> str | None:
    value = attributes.get("renews_at") or attributes.get("ends_at")
    return str(value) if value else None


def _failed_attempt_number(attributes: dict[str, Any]) -> int:
    for key in ("attempt_count", "payment_attempt", "retry_count"):
        value = attributes.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return 1


async def _fetch_user(user_id: str, db: Any | None = None) -> dict[str, Any] | None:
    supabase = db or await get_supabase_client()
    data = await _execute(
        supabase.table("users").select("*").eq("id", user_id).maybe_single()
    )
    return data if isinstance(data, dict) else None


async def _update_subscription(
    user_id: str,
    attributes: dict[str, Any],
    *,
    tier: str,
    status: str,
    db: Any | None = None,
) -> None:
    supabase = db or await get_supabase_client()
    payload: dict[str, Any] = {
        "tier": tier,
        "payment_provider": "lemonsqueezy",
        "subscription_status": status,
        "lemonsqueezy_customer_id": _str_or_none(attributes.get("customer_id")),
        "lemonsqueezy_subscription_id": _str_or_none(attributes.get("subscription_id"))
        or _str_or_none(attributes.get("id")),
        "current_period_end": _period_end(attributes),
    }
    await _execute(supabase.table("users").update(payload).eq("id", user_id))


def _notify(callback: Any, *args: Any) -> None:
    try:
        callback(*args)
    except Exception as exc:
        capture_exception(exc)


async def handle_webhook_event(
    event_name: str,
    data: dict[str, Any],
    custom_data: dict[str, Any],
    db: Any | None = None,
) -> None:
    attributes = data.get("attributes", {})
    if not isinstance(attributes, dict):
        attributes = {}
    attributes = {**attributes, "id": data.get("id")}

    user_id = _user_id(custom_data)
    if not user_id:
        return

    if event_name == "order_created":
        return

    if event_name in {"subscription_created", "subscription_updated"}:
        status = str(attributes.get("status") or "none")
        await _update_subscription(
            user_id,
            attributes,
            tier="premium" if status == "active" else "free",
            status=status,
            db=db,
        )
        return

    if event_name in {"subscription_cancelled", "subscription_expired"}:
        await _update_subscription(
            user_id,
            attributes,
            tier="free",
            status=str(attributes.get("status") or event_name),
            db=db,
        )
        return

    if event_name == "subscription_payment_success":
        await _update_subscription(
            user_id,
            attributes,
            tier="premium",
            status="active",
            db=db,
        )
        return

    if event_name == "subscription_payment_failed":
        user = await _fetch_user(user_id, db=db)
        attempt_number = _failed_attempt_number(attributes)
        if user:
            _notify(email_service.send_payment_failed, user, attempt_number)

        if attempt_number >= 3:
            await _update_subscription(
                user_id,
                attributes,
                tier="free",
                status="payment_failed",
                db=db,
            )
