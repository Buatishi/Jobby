from datetime import UTC, datetime
from typing import Any

import stripe

from app.config import settings
from app.database import get_supabase_client
from app.services import email_service
from app.services.account_deletion import capture_exception

stripe.api_key = settings.stripe_secret_key


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


async def _update_user_tier(
    user_id: str | None,
    tier: str,
    *,
    stripe_customer_id: str | None = None,
    db: Any | None = None,
) -> None:
    supabase = db or await get_supabase_client()
    payload: dict[str, Any] = {"tier": tier}
    if stripe_customer_id:
        payload["stripe_customer_id"] = stripe_customer_id

    if user_id:
        await _execute(supabase.table("users").update(payload).eq("id", user_id))
        return

    if stripe_customer_id:
        await _execute(
            supabase.table("users")
            .update({"tier": tier})
            .eq("stripe_customer_id", stripe_customer_id)
        )


async def _fetch_user(
    *,
    user_id: str | None = None,
    stripe_customer_id: str | None = None,
    db: Any | None = None,
) -> dict[str, Any] | None:
    supabase = db or await get_supabase_client()
    query = supabase.table("users").select("*")
    if user_id:
        query = query.eq("id", user_id)
    elif stripe_customer_id:
        query = query.eq("stripe_customer_id", stripe_customer_id)
    else:
        return None

    data = await _execute(query.single())
    return data if isinstance(data, dict) else None


def _metadata_user_id(payload: dict[str, Any]) -> str | None:
    metadata = payload.get("metadata")
    if isinstance(metadata, dict) and metadata.get("user_id"):
        return str(metadata["user_id"])
    if payload.get("client_reference_id"):
        return str(payload["client_reference_id"])
    return None


def _customer_id(payload: dict[str, Any]) -> str | None:
    customer = payload.get("customer")
    return str(customer) if customer else None


def _subscription_is_active(payload: dict[str, Any]) -> bool:
    return str(payload.get("status")) in {"active", "trialing"}


def _days_until(timestamp: Any) -> int:
    try:
        end_date = datetime.fromtimestamp(int(timestamp), tz=UTC)
    except (TypeError, ValueError, OSError):
        return 0
    remaining = end_date - datetime.now(UTC)
    return max(0, remaining.days)


def _attempt_number(payload: dict[str, Any]) -> int:
    for key in ("attempt_count", "attempt_number"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return 1


def _notify(callback: Any, *args: Any) -> None:
    try:
        callback(*args)
    except Exception as exc:
        capture_exception(exc)


def _subscription_payload(subscription: Any) -> dict[str, Any]:
    if isinstance(subscription, dict):
        return subscription

    metadata = getattr(subscription, "metadata", {}) or {}
    customer = getattr(subscription, "customer", None)
    status = getattr(subscription, "status", None)
    client_reference_id = getattr(subscription, "client_reference_id", None)
    return {
        "metadata": dict(metadata) if isinstance(metadata, dict) else {},
        "customer": customer,
        "status": status,
        "client_reference_id": client_reference_id,
    }


async def create_checkout_session(
    user_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=user_id,
        metadata={"user_id": user_id},
        subscription_data={"metadata": {"user_id": user_id}},
    )
    url = (
        session.get("url")
        if isinstance(session, dict)
        else getattr(session, "url", None)
    )
    if not url:
        raise RuntimeError("Stripe did not return a checkout URL.")
    return str(url)


async def handle_webhook(event: dict[str, Any], db: Any | None = None) -> None:
    event_type = str(event.get("type", ""))
    payload = event.get("data", {}).get("object", {})
    if not isinstance(payload, dict):
        return

    if event_type in {"customer.subscription.created", "subscription.created"}:
        await _update_user_tier(
            _metadata_user_id(payload),
            "premium" if _subscription_is_active(payload) else "free",
            stripe_customer_id=_customer_id(payload),
            db=db,
        )
        return

    if event_type in {"customer.subscription.updated", "subscription.updated"}:
        user_id = _metadata_user_id(payload)
        stripe_customer_id = _customer_id(payload)
        user = await _fetch_user(
            user_id=user_id,
            stripe_customer_id=stripe_customer_id,
            db=db,
        )
        await _update_user_tier(
            user_id,
            "premium" if _subscription_is_active(payload) else "free",
            stripe_customer_id=stripe_customer_id,
            db=db,
        )
        if user and payload.get("cancel_at_period_end") is True:
            _notify(
                email_service.send_subscription_expiring,
                user,
                _days_until(payload.get("current_period_end")),
            )
        if user and not _subscription_is_active(payload):
            _notify(email_service.send_subscription_expired, user)
            _notify(email_service.send_downgrade_notification, user)
        return

    if event_type in {"customer.subscription.deleted", "subscription.deleted"}:
        user_id = _metadata_user_id(payload)
        stripe_customer_id = _customer_id(payload)
        user = await _fetch_user(
            user_id=user_id,
            stripe_customer_id=stripe_customer_id,
            db=db,
        )
        await _update_user_tier(
            user_id,
            "free",
            stripe_customer_id=stripe_customer_id,
            db=db,
        )
        if user:
            _notify(email_service.send_subscription_expired, user)
            _notify(email_service.send_downgrade_notification, user)
        return

    if event_type == "invoice.payment_failed":
        user_id = _metadata_user_id(payload)
        stripe_customer_id = _customer_id(payload)
        subscription_id = payload.get("subscription")
        if not user_id and subscription_id:
            subscription = stripe.Subscription.retrieve(str(subscription_id))
            subscription_payload = _subscription_payload(subscription)
            user_id = _metadata_user_id(subscription_payload)
            stripe_customer_id = stripe_customer_id or _customer_id(
                subscription_payload
            )
        user = await _fetch_user(
            user_id=user_id,
            stripe_customer_id=stripe_customer_id,
            db=db,
        )
        await _update_user_tier(
            user_id,
            "free",
            stripe_customer_id=stripe_customer_id,
            db=db,
        )
        if user:
            _notify(email_service.send_payment_failed, user, _attempt_number(payload))
            _notify(email_service.send_downgrade_notification, user)
