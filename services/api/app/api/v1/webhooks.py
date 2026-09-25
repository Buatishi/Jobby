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


PROCESSED_EVENT_TTL_SECONDS = 60 * 60 * 24


async def _was_processed(event_key: str) -> bool:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        return await client.get(event_key) is not None
    finally:
        await client.aclose()


async def _mark_processed(event_key: str) -> None:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.set(event_key, "1", ex=PROCESSED_EVENT_TTL_SECONDS)
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
        if await _was_processed(event_key):
            return {"status": "ok"}
    except Exception as exc:
        # Sin Redis se procesa igual: repetir un evento solo vuelve a escribir el plan.
        capture_exception(exc)

    try:
        await handle_webhook_event(event_name, data, custom_data)
    except Exception as exc:
        capture_exception(exc)
        # Un error hace que LemonSqueezy reintente el aviso. Antes se respondía «ok» con
        # el evento ya marcado, y quien pagaba podía quedarse sin premium.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "No se pudo procesar el evento de Lemon Squeezy",
                "code": "LEMONSQUEEZY_EVENT_FAILED",
                "details": {},
            },
        ) from exc

    # Se marca recién ahora, cuando el evento ya quedó aplicado.
    try:
        await _mark_processed(event_key)
    except Exception as exc:
        capture_exception(exc)

    return {"status": "ok"}
