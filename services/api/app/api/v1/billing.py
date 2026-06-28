from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.services.stripe_service import create_checkout_session

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutSessionRequest(BaseModel):
    price_id: str
    success_url: HttpUrl
    cancel_url: HttpUrl


class CheckoutSessionResponse(BaseModel):
    url: str


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_billing_checkout_session(
    payload: CheckoutSessionRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CheckoutSessionResponse:
    try:
        checkout_url = await create_checkout_session(
            current_user.id,
            payload.price_id,
            str(payload.success_url),
            str(payload.cancel_url),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "No se pudo crear la sesión de Stripe",
                "code": "STRIPE_CHECKOUT_FAILED",
                "details": {"reason": str(exc)},
            },
        ) from exc
    return CheckoutSessionResponse(url=checkout_url)
