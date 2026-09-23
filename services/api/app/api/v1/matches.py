from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.models.jobs import JobDescription
from app.models.matches import MatchRatingUpdate, MatchReport

router = APIRouter(prefix="/matches", tags=["matches"])


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


async def _fetch_match(
    supabase: Any,
    match_or_job_id: str,
    user_id: str,
) -> dict[str, Any]:
    data = await _execute(
        supabase.table("job_matches")
        .select("*")
        .eq("id", match_or_job_id)
        .eq("user_id", user_id)
        .maybe_single()
    )
    if isinstance(data, dict):
        return data

    data = await _execute(
        supabase.table("job_matches")
        .select("*")
        .eq("job_id", match_or_job_id)
        .eq("user_id", user_id)
        .maybe_single()
    )
    if isinstance(data, dict):
        return data

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "Match no encontrado",
            "code": "MATCH_NOT_FOUND",
            "details": {},
        },
    )


async def _fetch_job(
    supabase: Any,
    job_id: str,
    user_id: str,
) -> JobDescription | None:
    data = await _execute(
        supabase.table("job_descriptions")
        .select("*")
        .eq("id", job_id)
        .eq("user_id", user_id)
        .maybe_single()
    )
    if isinstance(data, dict):
        return JobDescription.model_validate(data)
    return None


@router.get("/{match_id}", response_model=MatchReport)
async def get_match_report(
    match_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> MatchReport:
    match = await _fetch_match(supabase, match_id, current_user.id)
    job = await _fetch_job(supabase, str(match["job_id"]), current_user.id)
    return MatchReport.model_validate({**match, "job": job})


@router.patch("/{match_id}/rating", response_model=MatchReport)
async def update_match_rating(
    match_id: str,
    payload: MatchRatingUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> MatchReport:
    match = await _fetch_match(supabase, match_id, current_user.id)
    response = (
        await supabase.table("job_matches")
        .update({"user_rating": payload.rating})
        .eq("id", match["id"])
        .eq("user_id", current_user.id)
        .execute()
    )
    data = getattr(response, "data", None)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        match = data[0]
    elif isinstance(data, dict):
        match = data
    else:
        match = {**match, "user_rating": payload.rating}

    job = await _fetch_job(supabase, str(match["job_id"]), current_user.id)
    return MatchReport.model_validate({**match, "job": job})
