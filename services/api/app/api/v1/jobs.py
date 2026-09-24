import asyncio
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.models.jobs import (
    JobAnalysisRequest,
    JobAnalyzeResponse,
    JobDescription,
    JobUpdateRequest,
)
from app.services.rate_limits import (
    RateLimitExceededError,
    RateLimitKind,
    increment_rate_limit,
)
from app.services.scraper.url_guard import UnsafeUrlError, ensure_public_http_url
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
        .maybe_single()
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
        supabase.table("users").select("tier").eq("id", user_id).maybe_single()
    )
    if isinstance(data, dict) and isinstance(data.get("tier"), str):
        return str(data["tier"])
    return "free"


def _job_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "Job no encontrado",
            "code": "JOB_NOT_FOUND",
            "details": {},
        },
    )


async def _fetch_owned_job(supabase: Any, job_id: str, user_id: str) -> dict[str, Any]:
    # Un puesto ajeno responde igual que uno inexistente: no se revela que existe.
    data = await _execute(
        supabase.table("job_descriptions")
        .select("*")
        .eq("id", job_id)
        .eq("user_id", user_id)
        .maybe_single()
    )
    if not isinstance(data, dict):
        raise _job_not_found()
    return data


async def _has_rows_for_job(supabase: Any, table: str, job_id: str) -> bool:
    data = await _execute(
        supabase.table(table).select("id").eq("job_id", job_id).limit(1)
    )
    return isinstance(data, list) and len(data) > 0


async def _validate_analysis_request(payload: JobAnalysisRequest) -> None:
    if payload.source == "url" and not payload.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "La URL del puesto es requerida",
                "code": "JOB_URL_REQUIRED",
                "details": {},
            },
        )
    if payload.source == "url" and payload.url:
        try:
            await ensure_public_http_url(payload.url)
        except UnsafeUrlError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "La URL del puesto no es válida o no está permitida",
                    "code": "JOB_URL_INVALID",
                    "details": {},
                },
            ) from exc
    if payload.source == "text" and not payload.raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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
    await _validate_analysis_request(payload)
    profile = await _fetch_profile(supabase, current_user.id)
    completeness_pct = int(profile.get("completeness_pct") or 0)
    if completeness_pct < 60:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Completá al menos el 60% de tu perfil antes de analizar jobs",
                "code": "PROFILE_INCOMPLETE",
                "details": {"completeness_pct": completeness_pct},
            },
        )
    user_tier = await _fetch_user_tier(supabase, current_user.id)
    try:
        await increment_rate_limit(current_user.id, user_tier, RateLimitKind.JOBS)
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Límite mensual de análisis de jobs alcanzado",
                "code": "JOB_RATE_LIMIT_EXCEEDED",
                "details": {
                    "limit": exc.limit,
                    "reset_at": exc.reset_at.isoformat(),
                },
            },
        ) from exc

    job_id = str(uuid4())
    task_id = enqueue_job_analysis(
        job_id,
        current_user.id,
        payload.source,
        payload.url,
        payload.raw_text,
    )
    return JobAnalyzeResponse(
        job_id=job_id,
        task_id=task_id,
        profile_confidence="high" if completeness_pct >= 85 else "medium",
    )


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
    job_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> JobDescription:
    job = await _fetch_owned_job(supabase, str(job_id), current_user.id)
    return JobDescription.model_validate(job)


@router.patch("/{job_id}", response_model=JobDescription)
async def update_job(
    job_id: UUID,
    payload: JobUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> JobDescription:
    changes = payload.model_dump(include=payload.model_fields_set)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "No hay datos del puesto para actualizar",
                "code": "JOB_UPDATE_EMPTY",
                "details": {},
            },
        )

    job_key = str(job_id)
    job = await _fetch_owned_job(supabase, job_key, current_user.id)
    # El rango se valida solo si se toca el salario: un valor viejo mal detectado por
    # la IA no debe impedir corregir, por ejemplo, el título.
    if "salary_min" in changes or "salary_max" in changes:
        salary_min = changes.get("salary_min", job.get("salary_min"))
        salary_max = changes.get("salary_max", job.get("salary_max"))
        if (
            salary_min is not None
            and salary_max is not None
            and salary_min > salary_max
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "El salario mínimo no puede superar al máximo",
                    "code": "JOB_SALARY_RANGE_INVALID",
                    "details": {"salary_min": salary_min, "salary_max": salary_max},
                },
            )

    data = await _execute(
        supabase.table("job_descriptions")
        .update(changes)
        .eq("id", job_key)
        .eq("user_id", current_user.id)
    )
    if not isinstance(data, list) or not data:
        # Se borró entre la lectura y la escritura.
        raise _job_not_found()
    return JobDescription.model_validate(data[0])


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> None:
    job_key = str(job_id)
    await _fetch_owned_job(supabase, job_key, current_user.id)
    has_matches, has_interview_kits = await asyncio.gather(
        _has_rows_for_job(supabase, "job_matches", job_key),
        _has_rows_for_job(supabase, "interview_kits", job_key),
    )
    # La base borraría en cascada las comparaciones y los kits (ON DELETE CASCADE);
    # la Decisión 1 prefiere rechazar para que nadie pierda resultados sin querer.
    if has_matches or has_interview_kits:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": (
                    "El puesto tiene comparaciones o kits de entrevista y no se "
                    "puede eliminar"
                ),
                "code": "JOB_HAS_DEPENDENT_RESULTS",
                "details": {
                    "has_matches": has_matches,
                    "has_interview_kits": has_interview_kits,
                },
            },
        )

    await _execute(
        supabase.table("job_descriptions")
        .delete()
        .eq("id", job_key)
        .eq("user_id", current_user.id)
    )
