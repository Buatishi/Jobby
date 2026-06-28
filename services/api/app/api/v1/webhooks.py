import json
from typing import Any, cast

import stripe
from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.services.stripe_service import handle_webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request) -> dict[str, str]:
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Firma de Stripe faltante",
                "code": "STRIPE_SIGNATURE_MISSING",
                "details": {},
            },
        )

    try:
        event: Any = cast(Any, stripe.Webhook).construct_event(
            payload,
            signature,
            settings.stripe_webhook_secret,
        )
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Firma de Stripe inválida",
                "code": "STRIPE_SIGNATURE_INVALID",
                "details": {},
            },
        ) from exc

    event_payload = dict(event) if not isinstance(event, dict) else event
    if not event_payload:
        event_payload = json.loads(payload.decode("utf-8"))
    await handle_webhook(event_payload)
    return {"status": "ok"}
