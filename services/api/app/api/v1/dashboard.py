import asyncio
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.models.dashboard import DashboardMatch, DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)


async def _execute(query: Any) -> Any:
    try:
        response = await query.execute()
    except Exception:
        logger.exception("Dashboard query failed")
        return None
    return getattr(response, "data", None)


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value)
    return default


async def _missing_tip(
    supabase: Any,
    user_id: str,
    profile: dict[str, Any] | None,
) -> str | None:
    if not profile:
        return "Completá tu perfil base para mejorar la calidad del Match Score."

    documents = await _execute(
        supabase.table("uploaded_documents")
        .select("id")
        .eq("user_id", user_id)
        .eq("type", "cv")
        .eq("is_primary", True)
        .limit(1)
    )
    if not (isinstance(documents, list) and documents):
        return "Subí tu CV para empezar a recibir análisis."

    if not profile.get("linkedin_url"):
        return "Conectá tu LinkedIn para mejorar tu Reality Gap (+18 pts)."

    experiences = await _execute(
        supabase.table("experiences")
        .select("id")
        .eq("profile_id", str(profile.get("id") or ""))
        .limit(1)
    )
    if not (isinstance(experiences, list) and experiences):
        return "Agregá tu experiencia laboral (+12 pts)."

    field_tips = [
        ("headline", "Agregá un headline claro para mejorar la lectura inicial."),
        ("summary", "Sumá un resumen profesional con foco en tu rol objetivo."),
        ("target_role", "Definí tu rol objetivo para comparar contra puestos reales."),
        (
            "target_seniority",
            "Indicá tu seniority objetivo para calibrar expectativas del puesto.",
        ),
        (
            "work_modality",
            "Elegí tu modalidad de trabajo preferida para detectar fit operacional.",
        ),
        ("linkedin_url", "Conectá tu LinkedIn para reducir el Reality Gap."),
    ]

    for field_name, tip in field_tips:
        if not profile.get(field_name):
            return tip
    return None


async def _fetch_job(supabase: Any, job_id: str | None, user_id: str) -> dict[str, Any]:
    if not job_id:
        return {}

    data = await _execute(
        supabase.table("job_descriptions")
        .select("id,company_name,job_title,created_at")
        .eq("id", job_id)
        .eq("user_id", user_id)
        .single()
    )
    return data if isinstance(data, dict) else {}


async def _latest_matches(
    supabase: Any,
    user_id: str,
) -> list[DashboardMatch]:
    data = await _execute(
        supabase.table("job_matches")
        .select("id,job_id,match_score,created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(5)
    )
    if not isinstance(data, list):
        return []

    matches: list[DashboardMatch] = []
    rows = [row for row in data if isinstance(row, dict)]
    jobs = await asyncio.gather(
        *[_fetch_job(supabase, row.get("job_id"), user_id) for row in rows],
    )
    for row, job in zip(rows, jobs, strict=True):
        matches.append(
            DashboardMatch(
                id=str(row.get("job_id") or row.get("id")),
                job_id=str(row.get("job_id")) if row.get("job_id") else None,
                company_name=job.get("company_name"),
                job_title=job.get("job_title"),
                match_score=_as_int(row.get("match_score")),
                created_at=str(row.get("created_at") or job.get("created_at") or ""),
            )
        )
    return matches


async def _pending_count(supabase: Any, user_id: str) -> int:
    documents = await _execute(
        supabase.table("uploaded_documents")
        .select("id,status")
        .eq("user_id", user_id)
    )
    if not isinstance(documents, list):
        return 0

    return sum(
        1
        for document in documents
        if isinstance(document, dict)
        and document.get("status") in {"pending", "processing"}
    )


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> DashboardSummary:
    user_data, profile = await asyncio.gather(
        _execute(
            supabase.table("users")
            .select("email,full_name")
            .eq("id", current_user.id)
            .single()
        ),
        _execute(
            supabase.table("master_profiles")
            .select("*")
            .eq("user_id", current_user.id)
            .single()
        ),
    )
    profile_data = profile if isinstance(profile, dict) else None
    completeness_pct = _as_int(
        profile_data.get("completeness_pct") if profile_data else 0
    )
    latest_matches, missing_tip, pending_analyses_count = await asyncio.gather(
        _latest_matches(supabase, current_user.id),
        _missing_tip(supabase, current_user.id, profile_data),
        _pending_count(supabase, current_user.id),
    )
    match_scores = [
        match.match_score
        for match in latest_matches
        if isinstance(match.match_score, int)
    ]
    employability_score = (
        round(sum(match_scores) / len(match_scores))
        if match_scores
        else completeness_pct
    )

    return DashboardSummary(
        user_name=current_user.email
        or (user_data.get("email") if isinstance(user_data, dict) else None),
        full_name=user_data.get("full_name") if isinstance(user_data, dict) else None,
        employability_score=employability_score,
        completeness_pct=completeness_pct,
        missing_tip=missing_tip,
        pending_analyses_count=pending_analyses_count,
        latest_matches=latest_matches,
    )
