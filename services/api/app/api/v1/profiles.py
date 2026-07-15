from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.models.profiles import (
    EducationCreate,
    ExperienceCreate,
    LanguageCreate,
    MasterProfile,
    MasterProfileUpdate,
    RejectedSkillCreate,
    SkillCreate,
    UploadedDocument,
    UploadedDocumentCreate,
)
from app.models.reality_gap import RealityGapReport, RealityGapSkill
from app.services.reality_gap import score_reality_gap
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


async def _prepare_cv_slot_for_insert(
    supabase: Any,
    user_id: str,
    payload: UploadedDocumentCreate,
) -> None:
    if payload.type != "cv":
        return

    if payload.cv_slot is not None:
        await (
            supabase.table("uploaded_documents")
            .delete()
            .eq("user_id", user_id)
            .eq("type", "cv")
            .eq("cv_slot", payload.cv_slot)
            .execute()
        )

    if payload.is_primary:
        await (
            supabase.table("uploaded_documents")
            .update({"is_primary": False})
            .eq("user_id", user_id)
            .eq("type", "cv")
            .execute()
        )


async def _insert_profile_row(
    supabase: Any,
    table_name: str,
    profile_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = (
        await supabase.table(table_name)
        .insert({"profile_id": profile_id, **payload})
        .execute()
    )
    data = getattr(response, "data", None)
    if isinstance(data, list) and data:
        created_row = data[0]
        if isinstance(created_row, dict):
            return created_row
    if isinstance(data, dict):
        return data
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error": "No se pudo guardar el dato del perfil",
            "code": "PROFILE_DETAIL_CREATE_FAILED",
            "details": {"table": table_name},
        },
    )


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
    await _prepare_cv_slot_for_insert(supabase, current_user.id, payload)

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


@router.post("/skills", status_code=201)
async def create_profile_skill(
    payload: SkillCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> dict[str, Any]:
    profile = await _fetch_profile(supabase, current_user.id)
    skill = await _insert_profile_row(
        supabase,
        "skills",
        str(profile["id"]),
        {
            "name": payload.name,
            "category": payload.category,
            "level": payload.level,
            "in_cv": payload.in_cv,
            "confirmed": payload.confirmed,
        },
    )
    await _update_completeness(supabase, str(profile["id"]))
    return skill


@router.post("/rejected-skills", status_code=201)
async def create_rejected_profile_skill(
    payload: RejectedSkillCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> dict[str, Any]:
    profile = await _fetch_profile(supabase, current_user.id)
    return await _insert_profile_row(
        supabase,
        "rejected_skills",
        str(profile["id"]),
        payload.model_dump(),
    )


@router.post("/experiences", status_code=201)
async def create_profile_experience(
    payload: ExperienceCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> dict[str, Any]:
    profile = await _fetch_profile(supabase, current_user.id)
    experience = await _insert_profile_row(
        supabase,
        "experiences",
        str(profile["id"]),
        payload.model_dump(),
    )
    await _update_completeness(supabase, str(profile["id"]))
    return experience


@router.post("/educations", status_code=201)
async def create_profile_education(
    payload: EducationCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> dict[str, Any]:
    profile = await _fetch_profile(supabase, current_user.id)
    education = await _insert_profile_row(
        supabase,
        "educations",
        str(profile["id"]),
        payload.model_dump(),
    )
    await _update_completeness(supabase, str(profile["id"]))
    return education


@router.post("/languages", status_code=201)
async def create_profile_language(
    payload: LanguageCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> dict[str, Any]:
    profile = await _fetch_profile(supabase, current_user.id)
    language = await _insert_profile_row(
        supabase,
        "languages",
        str(profile["id"]),
        {"name": payload.name, "proficiency": payload.level},
    )
    await _update_completeness(supabase, str(profile["id"]))
    return language


@router.get("/reality-gap", response_model=RealityGapReport)
async def get_reality_gap(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> RealityGapReport:
    profile = await _fetch_profile(supabase, current_user.id)
    skills_response = (
        await supabase.table("skills")
        .select("*")
        .eq("profile_id", profile["id"])
        .eq("confirmed", True)
        .execute()
    )
    rejected_response = (
        await supabase.table("rejected_skills")
        .select("*")
        .eq("profile_id", profile["id"])
        .execute()
    )
    skills_data = getattr(skills_response, "data", [])
    rejected_data = getattr(rejected_response, "data", [])
    scored = score_reality_gap(
        [skill for skill in skills_data if isinstance(skill, dict)]
        if isinstance(skills_data, list)
        else [],
        [skill for skill in rejected_data if isinstance(skill, dict)]
        if isinstance(rejected_data, list)
        else [],
    )
    return RealityGapReport(
        profile_id=str(profile["id"]),
        skills=[RealityGapSkill.model_validate(skill) for skill in scored],
    )
