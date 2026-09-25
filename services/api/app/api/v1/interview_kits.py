from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.models.interview_kits import (
    InterviewKit,
    InterviewKitCreate,
    InterviewKitRatingUpdate,
)
from app.services.rate_limits import (
    RateLimitExceededError,
    RateLimitKind,
    increment_rate_limit,
)
from app.services.scraper.url_guard import (
    UnsafeUrlError,
    ensure_linkedin_host,
    ensure_public_http_url,
)
from app.tasks.analysis import enqueue_interview_kit

router = APIRouter(prefix="/interview-kits", tags=["interview-kits"])


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


async def _fetch_kit(supabase: Any, kit_id: str, user_id: str) -> dict[str, Any]:
    data = await _execute(
        supabase.table("interview_kits")
        .select("*")
        .eq("id", kit_id)
        .eq("user_id", user_id)
        .maybe_single()
    )
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Interview Kit no encontrado",
                "code": "INTERVIEW_KIT_NOT_FOUND",
                "details": {},
            },
        )
    return data


def _premium_required() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "Interview Kits requiere plan premium",
            "code": "PREMIUM_REQUIRED",
            "details": {},
        },
    )


def _rate_limit_error(exc: RateLimitExceededError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Límite mensual de Interview Kits alcanzado",
            "code": "INTERVIEW_KIT_RATE_LIMIT_EXCEEDED",
            "details": {
                "limit": exc.limit,
                "reset_at": exc.reset_at.isoformat(),
            },
        },
    )


async def _validate_linkedin_urls(payload: InterviewKitCreate) -> None:
    for url in (payload.company_linkedin_url, payload.interviewer_linkedin_url):
        if not url:
            continue
        try:
            ensure_linkedin_host(url)
            await ensure_public_http_url(url)
        except UnsafeUrlError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "La URL de LinkedIn no es válida",
                    "code": "LINKEDIN_URL_INVALID",
                    "details": {},
                },
            ) from exc


@router.post("", response_model=InterviewKit, status_code=202)
async def create_interview_kit(
    payload: InterviewKitCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> InterviewKit:
    user_tier = current_user.tier
    if user_tier != "premium":
        raise _premium_required()

    profile = await _fetch_profile(supabase, current_user.id)
    if int(profile.get("completeness_pct") or 0) < 100:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Completá tu perfil al 100% antes de generar kits",
                "code": "PROFILE_INCOMPLETE",
                "details": {"completeness_pct": profile.get("completeness_pct", 0)},
            },
        )
    await _validate_linkedin_urls(payload)
    try:
        await increment_rate_limit(current_user.id, user_tier, RateLimitKind.KITS)
    except RateLimitExceededError as exc:
        raise _rate_limit_error(exc) from exc

    response = (
        await supabase.table("interview_kits")
        .insert(
            {
                "user_id": current_user.id,
                "profile_id": profile["id"],
                "job_id": payload.job_id,
                "match_id": payload.match_id,
                "status": "pending",
                "prep_notes": {
                    "company_linkedin_url": payload.company_linkedin_url,
                    "interviewer_linkedin_url": payload.interviewer_linkedin_url,
                    "interviewer_name": payload.interviewer_name,
                    "interviewer_role": payload.interviewer_role,
                },
            }
        )
        .execute()
    )
    data = getattr(response, "data", None)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        kit = data[0]
    elif isinstance(data, dict):
        kit = data
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "No se pudo crear el Interview Kit",
                "code": "INTERVIEW_KIT_CREATE_FAILED",
                "details": {},
            },
        )

    kit["task_id"] = enqueue_interview_kit(str(kit["id"]), current_user.id)
    return InterviewKit.model_validate(kit)


@router.get("", response_model=list[InterviewKit])
async def list_interview_kits(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> list[InterviewKit]:
    data = await _execute(
        supabase.table("interview_kits")
        .select("*")
        .eq("user_id", current_user.id)
        .order("created_at", desc=True)
    )
    if not isinstance(data, list):
        return []
    return [InterviewKit.model_validate(kit) for kit in data if isinstance(kit, dict)]


@router.get("/{kit_id}", response_model=InterviewKit)
async def get_interview_kit(
    kit_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> InterviewKit:
    return InterviewKit.model_validate(
        await _fetch_kit(supabase, kit_id, current_user.id)
    )


@router.patch("/{kit_id}/rating", response_model=InterviewKit)
async def update_interview_kit_rating(
    kit_id: str,
    payload: InterviewKitRatingUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> InterviewKit:
    kit = await _fetch_kit(supabase, kit_id, current_user.id)
    data = await _execute(
        supabase.table("interview_kits")
        .update({"user_rating": payload.rating})
        .eq("id", kit["id"])
        .eq("user_id", current_user.id)
    )
    if isinstance(data, list) and data and isinstance(data[0], dict):
        kit = data[0]
    elif isinstance(data, dict):
        kit = data
    else:
        kit = {**kit, "user_rating": payload.rating}
    return InterviewKit.model_validate(kit)


@router.post("/{kit_id}/regenerate", response_model=InterviewKit, status_code=202)
async def regenerate_interview_kit(
    kit_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> InterviewKit:
    user_tier = current_user.tier
    if user_tier != "premium":
        raise _premium_required()
    kit = await _fetch_kit(supabase, kit_id, current_user.id)
    try:
        await increment_rate_limit(current_user.id, user_tier, RateLimitKind.KITS)
    except RateLimitExceededError as exc:
        raise _rate_limit_error(exc) from exc

    data = await _execute(
        supabase.table("interview_kits")
        .update({"status": "pending", "error_msg": None})
        .eq("id", kit["id"])
        .eq("user_id", current_user.id)
    )
    if isinstance(data, list) and data and isinstance(data[0], dict):
        kit = data[0]
    elif isinstance(data, dict):
        kit = data
    else:
        kit = {**kit, "status": "pending", "error_msg": None}
    kit["task_id"] = enqueue_interview_kit(str(kit["id"]), current_user.id)
    return InterviewKit.model_validate(kit)
