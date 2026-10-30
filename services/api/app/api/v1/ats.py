import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.public_errors import public_error_message
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
from app.services.ai_gateway.errors import ProviderUnavailableError
from app.services.ats_analyzer.cv_optimizer import (
    optimize_cv_sections,
    score_after_optimization,
)
from app.services.ats_analyzer.format_checker import (
    check_cv_format,
    format_was_evaluated,
)
from app.services.ats_analyzer.keyword_matcher import analyze_keywords
from app.services.ats_analyzer.report_store import (
    fetch_report_row,
    keywords_from_row,
    report_from_row,
    save_report,
    skill_vector_loader,
)
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


async def _build_ats_report(
    job_id: str,
    job: dict[str, Any],
    primary_cv: dict[str, Any],
    supabase: Any,
    keywords: list[str] | None = None,
) -> ATSReport:
    # `keywords` son las que el puesto ya tenía: sin ellas se consulta a la IA, que
    # daría otras cada vez.
    keyword_result = await analyze_keywords(
        job,
        primary_cv,
        keywords=keywords,
        saved_vectors=skill_vector_loader(supabase, primary_cv),
    )
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
        format_evaluated=format_was_evaluated(primary_cv),
    )


async def _calculate_and_save_report(
    supabase: Any,
    user_id: str,
    job_id: str,
    job: dict[str, Any],
    primary_cv: dict[str, Any],
    saved_row: dict[str, Any] | None,
) -> ATSReport:
    report = await _build_ats_report(
        job_id, job, primary_cv, supabase, keywords_from_row(saved_row)
    )
    await save_report(supabase, user_id, primary_cv, report)
    return report


async def _spend_daily_ats_query(current_user: CurrentUser) -> None:
    try:
        await increment_rate_limit(
            current_user.id, current_user.tier, RateLimitKind.ATS
        )
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


@router.get("/{job_id}", response_model=ATSReport)
async def get_ats_report(
    job_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> ATSReport:
    job = await _fetch_job(supabase, job_id, current_user.id)
    primary_cv, saved_row = await asyncio.gather(
        _fetch_primary_cv(supabase, current_user.id),
        fetch_report_row(supabase, job_id, current_user.id),
    )
    # Volver a mirar un reporte ya calculado es una lectura: no usa IA ni vectores y no
    # gasta el límite diario. Solo calcular uno nuevo (o rehacerlo tras cambiar el CV
    # principal) cuenta.
    saved = report_from_row(saved_row, job_id, primary_cv)
    if saved is not None:
        return saved

    await _spend_daily_ats_query(current_user)
    return await _calculate_and_save_report(
        supabase, current_user.id, job_id, job, primary_cv, saved_row
    )


@router.post("/optimize", response_model=ATSOptimizeResponse)
async def optimize_ats_cv(
    payload: ATSOptimizeRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> ATSOptimizeResponse:
    user_tier = current_user.tier
    job = await _fetch_job(supabase, payload.job_id, current_user.id)
    primary_cv = await _fetch_primary_cv(supabase, current_user.id)
    try:
        await increment_rate_limit(
            current_user.id,
            user_tier,
            RateLimitKind.CV_OPTIMIZATION,
        )
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Límite mensual de CV optimizados alcanzado",
                "code": "CV_OPTIMIZATION_RATE_LIMIT_EXCEEDED",
                "details": {
                    "limit": exc.limit,
                    "reset_at": exc.reset_at.isoformat(),
                },
            },
        ) from exc

    # Parte del mismo reporte que la persona vio; si no hay uno vigente, lo calcula y lo
    # deja guardado (este endpoint tiene su propio límite mensual).
    saved_row = await fetch_report_row(supabase, payload.job_id, current_user.id)
    ats_report = report_from_row(saved_row, payload.job_id, primary_cv)
    if ats_report is None:
        ats_report = await _calculate_and_save_report(
            supabase, current_user.id, payload.job_id, job, primary_cv, saved_row
        )
    try:
        sections = await optimize_cv_sections(
            primary_cv,
            job,
            ats_report.keyword_matches,
            "premium" if user_tier == "premium" else "free",
        )
    except ProviderUnavailableError as exc:
        # Ningún plan de IA respondió: el detalle queda en los logs, no en la respuesta.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": public_error_message(exc),
                "code": "AI_PROVIDER_UNAVAILABLE",
                "details": {},
            },
        ) from exc
    penalty = sum(issue.penalty for issue in ats_report.format_issues)
    return ATSOptimizeResponse(
        job_id=payload.job_id,
        sections=sections,
        ats_score_before=ats_report.ats_score,
        ats_score_after=score_after_optimization(
            sections,
            ats_report.keyword_matches,
            penalty,
        ),
    )
