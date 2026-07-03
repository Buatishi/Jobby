import json

from fastapi import APIRouter, HTTPException, Request, status
from redis.asyncio import Redis

from app.config import settings
from app.services.account_deletion import capture_exception
from app.services.lemonsqueezy_service import (
    handle_webhook_event,
    verify_webhook_signature,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _already_processed(event_key: str) -> bool:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        was_set = await client.set(event_key, "1", ex=60 * 60 * 24, nx=True)
        return was_set is None
    finally:
        await client.aclose()


@router.post("/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request) -> dict[str, str]:
    raw_body = await request.body()
    signature = request.headers.get("X-Signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Firma de Lemon Squeezy faltante",
                "code": "LEMONSQUEEZY_SIGNATURE_MISSING",
                "details": {},
            },
        )

    if not verify_webhook_signature(raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Firma de Lemon Squeezy invalida",
                "code": "LEMONSQUEEZY_SIGNATURE_INVALID",
                "details": {},
            },
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Payload invalido",
                "code": "LEMONSQUEEZY_INVALID_PAYLOAD",
                "details": {},
            },
        ) from exc

    meta = payload.get("meta", {})
    data = payload.get("data", {})
    event_name = meta.get("event_name") if isinstance(meta, dict) else None
    custom_data = meta.get("custom_data", {}) if isinstance(meta, dict) else {}
    data_id = data.get("id") if isinstance(data, dict) else None

    if not isinstance(event_name, str) or not isinstance(data, dict):
        return {"status": "ok"}
    if not isinstance(custom_data, dict):
        custom_data = {}

    event_key = f"lemonsqueezy:webhook:{event_name}:{data_id or 'unknown'}"
    try:
        if await _already_processed(event_key):
            return {"status": "ok"}
    except Exception as exc:
        capture_exception(exc)

    try:
        await handle_webhook_event(event_name, data, custom_data)
    except Exception as exc:
        capture_exception(exc)

    return {"status": "ok"}
