from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.models.jobs import JobAnalysisRequest, JobAnalyzeResponse, JobDescription
from app.tasks.analysis import enqueue_job_analysis

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


async def _fetch_profile(supabase: Any, user_id: str) -> dict[str, Any]:
    data = await _execute(
        supabase.table("master_profiles")
        .select("*")
        .eq("user_id", user_id)
        .single()
    )
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Perfil no encontrado",
                "code": "PROFILE_NOT_FOUND",
                "details": {},
            },
        )
    return data


async def _fetch_user_tier(supabase: Any, user_id: str) -> str:
    data = await _execute(
        supabase.table("users").select("tier").eq("id", user_id).single()
    )
    if isinstance(data, dict) and isinstance(data.get("tier"), str):
        return str(data["tier"])
    return "free"


def _validate_analysis_request(payload: JobAnalysisRequest) -> None:
    if payload.source == "url" and not payload.url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "La URL del puesto es requerida",
                "code": "JOB_URL_REQUIRED",
                "details": {},
            },
        )
    if payload.source == "text" and not payload.raw_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "El texto del puesto es requerido",
                "code": "JOB_TEXT_REQUIRED",
                "details": {},
            },
        )


@router.post("/analyze", response_model=JobAnalyzeResponse, status_code=202)
async def analyze_job(
    payload: JobAnalysisRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> JobAnalyzeResponse:
    _validate_analysis_request(payload)
    profile = await _fetch_profile(supabase, current_user.id)
    if int(profile.get("completeness_pct") or 0) < 100:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Completá tu perfil al 100% antes de analizar jobs",
                "code": "PROFILE_INCOMPLETE",
                "details": {"completeness_pct": profile.get("completeness_pct", 0)},
            },
        )

    job_id = str(uuid4())
    task_id = enqueue_job_analysis(
        job_id,
        current_user.id,
        payload.source,
        payload.url,
        payload.raw_text,
    )
    return JobAnalyzeResponse(job_id=job_id, task_id=task_id)


@router.get("", response_model=list[JobDescription])
async def list_jobs(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> list[JobDescription]:
    user_tier = await _fetch_user_tier(supabase, current_user.id)
    query = (
        supabase.table("job_descriptions")
        .select("*")
        .eq("user_id", current_user.id)
        .order("created_at", desc=True)
    )
    if user_tier != "premium":
        query = query.limit(10)

    data = await _execute(query)
    if not isinstance(data, list):
        return []
    return [JobDescription.model_validate(job) for job in data if isinstance(job, dict)]


@router.get("/{job_id}", response_model=JobDescription)
async def get_job(
    job_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> JobDescription:
    data = await _execute(
        supabase.table("job_descriptions")
        .select("*")
        .eq("id", job_id)
        .eq("user_id", current_user.id)
        .single()
    )
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Job no encontrado",
                "code": "JOB_NOT_FOUND",
                "details": {},
            },
        )
    return JobDescription.model_validate(data)
