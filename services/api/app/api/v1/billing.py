from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.services.account_deletion import capture_exception
from app.services.lemonsqueezy_service import create_checkout_url

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_billing_checkout(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CheckoutResponse:
    try:
        checkout_url = await create_checkout_url(
            current_user.id, current_user.email or ""
        )
    except Exception as exc:
        capture_exception(exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Los pagos todavía no están disponibles",
                "code": "BILLING_CHECKOUT_FAILED",
                "details": {},
            },
        ) from exc
    return CheckoutResponse(checkout_url=checkout_url)
