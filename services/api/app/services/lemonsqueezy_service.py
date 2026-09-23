import hashlib
import hmac
from typing import Any
from urllib.parse import urlencode

from app.config import settings
from app.database import get_supabase_client
from app.services import email_service
from app.services.account_deletion import capture_exception


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


def build_checkout_url(user_id: str, user_email: str) -> str:
    if not settings.lemonsqueezy_store_id:
        raise RuntimeError("Missing Lemon Squeezy store id.")
    if not settings.lemonsqueezy_premium_variant_id:
        raise RuntimeError("Missing Lemon Squeezy premium variant id.")
    if not user_email:
        raise RuntimeError("User email is required to create checkout.")

    base_url = (
        f"https://{settings.lemonsqueezy_store_id}.lemonsqueezy.com"
        f"/checkout/buy/{settings.lemonsqueezy_premium_variant_id}"
    )
    query = urlencode(
        {
            "checkout[email]": user_email,
            "checkout[custom][user_id]": user_id,
        }
    )
    return f"{base_url}?{query}"


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
