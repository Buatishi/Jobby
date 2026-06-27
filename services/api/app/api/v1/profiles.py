from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.models.profiles import (
    MasterProfile,
    MasterProfileUpdate,
    UploadedDocument,
    UploadedDocumentCreate,
)
from app.tasks import parsing as parsing_tasks

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


async def _fetch_document(
    supabase: Any,
    document_id: str,
    user_id: str,
) -> dict[str, Any]:
    response = (
        await supabase.table("uploaded_documents")
        .select("*")
        .eq("id", document_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    data = getattr(response, "data", None)
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Documento no encontrado",
                "code": "DOCUMENT_NOT_FOUND",
                "details": {},
            },
        )
    return data


async def _update_completeness(supabase: Any, profile_id: str) -> None:
    await supabase.rpc("compute_completeness", {"p_id": profile_id}).execute()


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


@router.post("/documents", response_model=UploadedDocument, status_code=201)
async def create_profile_document(
    payload: UploadedDocumentCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> UploadedDocument:
    document_payload = {
        **payload.model_dump(),
        "user_id": current_user.id,
        "status": "pending",
    }
    response = (
        await supabase.table("uploaded_documents")
        .insert(document_payload)
        .execute()
    )
    created_data = getattr(response, "data", None)
    if isinstance(created_data, list) and created_data:
        document = created_data[0]
    elif isinstance(created_data, dict):
        document = created_data
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "No se pudo registrar el documento",
                "code": "DOCUMENT_CREATE_FAILED",
                "details": {},
            },
        )

    task_id = parsing_tasks.enqueue_parse_cv(str(document["id"]))
    document["task_id"] = task_id
    return UploadedDocument.model_validate(document)


@router.patch("/documents/{document_id}/set-primary", response_model=UploadedDocument)
async def set_primary_profile_document(
    document_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> UploadedDocument:
    response = await (
        supabase.rpc(
            "set_primary_uploaded_document",
            {"p_user_id": current_user.id, "p_document_id": document_id},
        )
        .execute()
    )
    document = getattr(response, "data", None)
    if not isinstance(document, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Documento no encontrado",
                "code": "DOCUMENT_NOT_FOUND",
                "details": {},
            },
        )

    task_id = parsing_tasks.enqueue_parse_cv(document_id)
    document["task_id"] = task_id
    return UploadedDocument.model_validate(document)


@router.delete("/documents/{document_id}", status_code=204)
async def delete_profile_document(
    document_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> None:
    document = await _fetch_document(supabase, document_id, current_user.id)
    await (
        supabase.table("uploaded_documents")
        .delete()
        .eq("id", document_id)
        .eq("user_id", current_user.id)
        .execute()
    )
    await _update_completeness(supabase, str(document["profile_id"]))
