from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.models.profiles import MasterProfile, MasterProfileUpdate

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "Perfil no encontrado",
            "code": "PROFILE_NOT_FOUND",
            "details": {},
        },
    )


async def _fetch_profile(supabase: Any, user_id: str) -> dict[str, Any]:
    response = (
        await supabase.table("master_profiles")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    data = getattr(response, "data", None)
    if not isinstance(data, dict):
        raise _not_found()

    return data


@router.get("/me", response_model=MasterProfile)
async def get_my_profile(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> MasterProfile:
    profile = await _fetch_profile(supabase, current_user.id)
    return MasterProfile.model_validate(profile)


@router.patch("/me", response_model=MasterProfile)
async def update_my_profile(
    payload: MasterProfileUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> MasterProfile:
    profile = await _fetch_profile(supabase, current_user.id)
    updates = payload.to_update_payload()

    if updates:
        updated_response = (
            await supabase.table("master_profiles")
            .update(updates)
            .eq("id", profile["id"])
            .execute()
        )
        updated_data = getattr(updated_response, "data", None)
        if isinstance(updated_data, list) and updated_data:
            profile = updated_data[0]
        elif isinstance(updated_data, dict):
            profile = updated_data
        else:
            profile = {**profile, **updates}

    rpc_response = await supabase.rpc(
        "compute_completeness",
        {"p_id": profile["id"]},
    ).execute()
    completeness = getattr(rpc_response, "data", None)
    if isinstance(completeness, int):
        completion_response = (
            await supabase.table("master_profiles")
            .update({"completeness_pct": completeness})
            .eq("id", profile["id"])
            .execute()
        )
        completion_data = getattr(completion_response, "data", None)
        if isinstance(completion_data, list) and completion_data:
            profile = completion_data[0]
        else:
            profile = {**profile, "completeness_pct": completeness}

    return MasterProfile.model_validate(profile)
