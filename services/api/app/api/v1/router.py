from fastapi import APIRouter

from app.api.v1 import ats, jobs, matches, profiles, tasks
from app.api.v1.routes import health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(profiles.router)
api_router.include_router(tasks.router)
api_router.include_router(jobs.router)
api_router.include_router(matches.router)
api_router.include_router(ats.router)
