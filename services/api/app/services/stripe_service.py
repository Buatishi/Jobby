from typing import Any

import stripe

from app.config import settings
from app.database import get_supabase_client

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
        await _update_user_tier(
            _metadata_user_id(payload),
            "premium" if _subscription_is_active(payload) else "free",
            stripe_customer_id=_customer_id(payload),
            db=db,
        )
        return

    if event_type in {"customer.subscription.deleted", "subscription.deleted"}:
        await _update_user_tier(
            _metadata_user_id(payload),
            "free",
            stripe_customer_id=_customer_id(payload),
            db=db,
        )
        return

    if event_type == "invoice.payment_failed":
        user_id = _metadata_user_id(payload)
        stripe_customer_id = _customer_id(payload)
        subscription_id = payload.get("subscription")
        if not user_id and subscription_id:
            subscription = stripe.Subscription.retrieve(str(subscription_id))
            subscription_payload = (
                dict(subscription)
                if not isinstance(subscription, dict)
                else subscription
            )
            user_id = _metadata_user_id(subscription_payload)
            stripe_customer_id = stripe_customer_id or _customer_id(
                subscription_payload
            )
        await _update_user_tier(
            user_id,
            "free",
            stripe_customer_id=stripe_customer_id,
            db=db,
        )
