from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.models.dashboard import DashboardMatch, DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value)
    return default


def _missing_tip(profile: dict[str, Any] | None) -> str | None:
    if not profile:
        return "Completá tu perfil base para mejorar la calidad del Match Score."

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
    for row in data:
        if not isinstance(row, dict):
            continue
        job = await _fetch_job(supabase, row.get("job_id"), user_id)
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
    user_data = await _execute(
        supabase.table("users")
        .select("email")
        .eq("id", current_user.id)
        .single()
    )
    profile = await _execute(
        supabase.table("master_profiles")
        .select("*")
        .eq("user_id", current_user.id)
        .single()
    )
    profile_data = profile if isinstance(profile, dict) else None
    completeness_pct = _as_int(
        profile_data.get("completeness_pct") if profile_data else 0
    )
    latest_matches = await _latest_matches(supabase, current_user.id)
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
        employability_score=employability_score,
        completeness_pct=completeness_pct,
        missing_tip=_missing_tip(profile_data),
        pending_analyses_count=await _pending_count(supabase, current_user.id),
        latest_matches=latest_matches,
    )
