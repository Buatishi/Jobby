from fastapi import APIRouter

from app.models.health import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    return HealthResponse(status="ok")
