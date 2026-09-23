from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.ats import (
    ATSFormatIssue,
    ATSKeywordMatch,
    ATSOptimizeRequest,
    ATSOptimizeResponse,
    ATSReport,
)
from app.models.auth import CurrentUser
from app.services.ats_analyzer.cv_optimizer import optimize_cv_sections
from app.services.ats_analyzer.format_checker import check_cv_format
from app.services.ats_analyzer.keyword_matcher import analyze_keywords
from app.services.ats_analyzer.scoring import compute_ats_score
from app.services.rate_limits import (
    RateLimitExceededError,
    RateLimitKind,
    increment_rate_limit,
)

router = APIRouter(prefix="/ats", tags=["ats"])


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


async def _fetch_job(supabase: Any, job_id: str, user_id: str) -> dict[str, Any]:
    data = await _execute(
        supabase.table("job_descriptions")
        .select("*")
        .eq("id", job_id)
        .eq("user_id", user_id)
        .maybe_single()
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
    return data


async def _fetch_primary_cv(supabase: Any, user_id: str) -> dict[str, Any]:
    data = await _execute(
        supabase.table("uploaded_documents")
        .select("*")
        .eq("user_id", user_id)
        .eq("type", "cv")
        .eq("is_primary", True)
        .maybe_single()
    )
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "CV primario no encontrado",
                "code": "PRIMARY_CV_NOT_FOUND",
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


async def _build_ats_report(
    job_id: str,
    job: dict[str, Any],
    primary_cv: dict[str, Any],
) -> ATSReport:
    keyword_result = await analyze_keywords(job, primary_cv)
    format_issues = check_cv_format(primary_cv)
    ats_score = compute_ats_score(keyword_result.matches, format_issues)

    return ATSReport(
        job_id=job_id,
        ats_score=ats_score,
        keyword_matches=[
            ATSKeywordMatch(
                keyword=match.keyword,
                status=match.status,
                matched_text=match.matched_text,
            )
            for match in keyword_result.matches
        ],
        format_issues=[
            ATSFormatIssue(
                code=issue.code,
                message=issue.message,
                penalty=issue.penalty,
            )
            for issue in format_issues
        ],
    )


@router.get("/{job_id}", response_model=ATSReport)
async def get_ats_report(
    job_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> ATSReport:
    job = await _fetch_job(supabase, job_id, current_user.id)
    primary_cv = await _fetch_primary_cv(supabase, current_user.id)
    user_tier = await _fetch_user_tier(supabase, current_user.id)
    try:
        await increment_rate_limit(current_user.id, user_tier, RateLimitKind.ATS)
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Límite diario de ATS alcanzado",
                "code": "ATS_RATE_LIMIT_EXCEEDED",
                "details": {
                    "limit": exc.limit,
                    "reset_at": exc.reset_at.isoformat(),
                },
            },
        ) from exc

    return await _build_ats_report(job_id, job, primary_cv)


@router.post("/optimize", response_model=ATSOptimizeResponse)
async def optimize_ats_cv(
    payload: ATSOptimizeRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> ATSOptimizeResponse:
    user_tier = await _fetch_user_tier(supabase, current_user.id)
    if user_tier != "premium":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "CV Optimizer requiere plan premium",
                "code": "PREMIUM_REQUIRED",
                "details": {},
            },
        )

    job = await _fetch_job(supabase, payload.job_id, current_user.id)
    primary_cv = await _fetch_primary_cv(supabase, current_user.id)
    ats_report = await _build_ats_report(payload.job_id, job, primary_cv)
    sections = await optimize_cv_sections(
        primary_cv,
        job,
        ats_report.keyword_matches,
    )
    return ATSOptimizeResponse(job_id=payload.job_id, sections=sections)
