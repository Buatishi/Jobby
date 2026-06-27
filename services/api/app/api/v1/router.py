from fastapi import APIRouter

from app.api.v1 import profiles
from app.api.v1.routes import health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(profiles.router)
