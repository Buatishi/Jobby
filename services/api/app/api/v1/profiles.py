import asyncio
import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from postgrest.exceptions import APIError

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.models.profiles import (
    EducationCreate,
    EducationUpdate,
    ExperienceCreate,
    ExperienceUpdate,
    LanguageCreate,
    LanguageUpdate,
    LinkedInDocument,
    LinkedInStatus,
    MasterProfile,
    MasterProfileUpdate,
    PrintableCV,
    ProfileDetails,
    ProfileEducationItem,
    ProfileExperienceItem,
    ProfileLanguageItem,
    RejectedSkillCreate,
    SkillCreate,
    UploadedDocument,
    UploadedDocumentCreate,
)
from app.models.reality_gap import RealityGapReport, RealityGapSkill
from app.services.account_deletion import capture_exception, remove_storage_objects
from app.services.cv_parser.merge_logic import normalize_skill_key
from app.services.printable_cv import build_printable_cv
from app.services.profile_completeness import refresh_completeness
from app.services.rate_limits import (
    RateLimitExceededError,
    RateLimitKind,
    increment_rate_limit,
)
from app.services.reality_gap import score_reality_gap
from app.tasks import parsing as parsing_tasks

logger = logging.getLogger("jobmatch.api")

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


def _document_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "Documento no encontrado",
            "code": "DOCUMENT_NOT_FOUND",
            "details": {},
        },
    )


# SQLSTATE de un RAISE EXCEPTION sin código propio en PL/pgSQL.
RAISED_EXCEPTION = "P0001"


def _ensure_own_storage_path(storage_path: str, supabase_uid: str) -> None:
    """El archivo tiene que estar dentro de la carpeta de la persona en el bucket.

    La API lo descarga con la clave de servicio, que no pasa por las políticas del
    bucket: sin esta verificación, registrar la ruta del CV de otra persona haría que se
    procese y se muestre como propio. El navegador sube a `<uid>/<uuid>-<nombre>`.
    """
    segments = storage_path.split("/")
    if (
        len(segments) < 2
        or segments[0] != supabase_uid
        or any(segment in {"", ".", ".."} for segment in segments)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "La ruta del archivo no es válida",
                "code": "INVALID_STORAGE_PATH",
                "details": {},
            },
        )


async def _enforce_document_upload_limit(current_user: CurrentUser) -> None:
    """Tope diario contra abuso: cada registro encola un parseo con IA que tiene costo.

    Si Redis no responde se deja pasar. Cargar el CV es el primer paso del onboarding y
    hasta ahora no dependía de Redis (la tarea cae a modo local si falta el broker): el
    tope no tiene que volverlo una caída más. El error se reporta igual.
    """
    try:
        await increment_rate_limit(
            current_user.id,
            current_user.tier,
            RateLimitKind.DOCUMENT_UPLOADS,
        )
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Límite diario de cargas de documentos alcanzado",
                "code": "DOCUMENT_UPLOAD_RATE_LIMIT_EXCEEDED",
                "details": {
                    "limit": exc.limit,
                    "reset_at": exc.reset_at.isoformat(),
                },
            },
        ) from exc
    except Exception as exc:
        logger.warning("No se pudo comprobar el tope de cargas de documentos: %s", exc)
        capture_exception(exc)


async def _fetch_profile(supabase: Any, user_id: str) -> dict[str, Any]:
    response = (
        await supabase.table("master_profiles")
        .select("*")
        .eq("user_id", user_id)
        .maybe_single()
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
        .maybe_single()
        .execute()
    )
    data = getattr(response, "data", None)
    if not isinstance(data, dict):
        raise _document_not_found()
    return data


async def _update_completeness(supabase: Any, profile_id: str) -> int | None:
    """Recalcula y guarda el porcentaje del perfil.

    Corre después de una escritura que ya se hizo: si el recálculo falla se reporta y se
    sigue, y el valor se corrige en el próximo cambio. Antes el RPC devolvía el número y
    nadie lo guardaba, así que el porcentaje solo se actualizaba al editar el perfil.
    """
    try:
        return await refresh_completeness(supabase, profile_id)
    except Exception as exc:
        logger.warning("No se pudo recalcular el porcentaje del perfil: %s", exc)
        capture_exception(exc)
        return None


async def _remove_stored_files(supabase: Any, storage_paths: list[str]) -> None:
    """Borra del bucket los archivos de documentos cuya fila ya se borró.

    Antes solo se borraba la fila: el archivo quedaba en el bucket sin nada que lo
    apuntara, y la baja de la cuenta (que borra las filas en cascada) ya no podía
    encontrarlo. Va después de borrar la fila y, si falla, no frena la operación: se
    reporta y el archivo sobrante lo barre la baja de la cuenta por la carpeta del uid.
    """
    if not storage_paths:
        return
    try:
        await remove_storage_objects(supabase, storage_paths)
    except Exception as exc:
        logger.warning(
            "No se pudo borrar un archivo del bucket: %s", type(exc).__name__
        )
        capture_exception(exc)


async def _delete_own_documents(supabase: Any, user_id: str, **filters: Any) -> None:
    """Borra los documentos de la persona que cumplen `filters`, con sus archivos."""

    def scoped(query: Any) -> Any:
        query = query.eq("user_id", user_id)
        for column, value in filters.items():
            query = query.eq(column, value)
        return query

    response = await scoped(
        supabase.table("uploaded_documents").select("storage_path")
    ).execute()
    rows = getattr(response, "data", None) or []
    await scoped(supabase.table("uploaded_documents").delete()).execute()
    await _remove_stored_files(
        supabase,
        [str(row["storage_path"]) for row in rows if row.get("storage_path")],
    )


async def _prepare_cv_slot_for_insert(
    supabase: Any,
    user_id: str,
    payload: UploadedDocumentCreate,
) -> None:
    if payload.type == "linkedin":
        # Un solo PDF de LinkedIn por persona: el nuevo reemplaza al anterior.
        await _delete_own_documents(supabase, user_id, type="linkedin")
        return

    if payload.type != "cv":
        return

    if payload.cv_slot is not None:
        await _delete_own_documents(
            supabase, user_id, type="cv", cv_slot=payload.cv_slot
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


async def _profile_rows(
    supabase: Any,
    table_name: str,
    columns: str,
    profile_id: str,
    newest_first: bool = False,
) -> list[dict[str, Any]]:
    query = supabase.table(table_name).select(columns).eq("profile_id", profile_id)
    if newest_first:
        query = query.order("created_at", desc=True)
    response = await query.execute()
    data = getattr(response, "data", None)
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


async def _primary_cv(supabase: Any, user_id: str) -> dict[str, Any] | None:
    response = (
        await supabase.table("uploaded_documents")
        .select("parsed_data")
        .eq("user_id", user_id)
        .eq("type", "cv")
        .eq("is_primary", True)
        .maybe_single()
        .execute()
    )
    data = getattr(response, "data", None)
    return data if isinstance(data, dict) else None


@router.get("/linkedin", response_model=LinkedInStatus)
async def get_linkedin_status(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> LinkedInStatus:
    """La URL de LinkedIn y el estado del PDF: la tarjeta de «Mi perfil» los muestra."""
    profile = await _fetch_profile(supabase, current_user.id)
    profile_id = str(profile["id"])
    documents, skills = await asyncio.gather(
        _profile_rows(
            supabase,
            "uploaded_documents",
            "id,type,status,original_filename,error_msg,created_at",
            profile_id,
            newest_first=True,
        ),
        _profile_rows(supabase, "skills", "in_linkedin", profile_id),
    )
    document = next(
        (row for row in documents if row.get("type") == "linkedin"), None
    )
    in_linkedin = sum(1 for skill in skills if skill.get("in_linkedin") is True)
    return LinkedInStatus(
        profile_id=profile_id,
        linkedin_url=profile.get("linkedin_url") or None,
        document=LinkedInDocument(**document) if document else None,
        skills_in_linkedin=in_linkedin,
    )


@router.get("/cv", response_model=PrintableCV)
async def get_printable_cv(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> PrintableCV:
    """Datos del CV descargable: perfil confirmado y encabezado leído del CV."""
    profile = await _fetch_profile(supabase, current_user.id)
    profile_id = str(profile["id"])
    (
        primary_cv,
        skills,
        experiences,
        educations,
        languages,
        certifications,
    ) = await asyncio.gather(
        _primary_cv(supabase, current_user.id),
        _profile_rows(supabase, "skills", "name", profile_id),
        _profile_rows(
            supabase,
            "experiences",
            "company,title,started_at,ended_at,is_current,description,achievements",
            profile_id,
        ),
        _profile_rows(
            supabase,
            "educations",
            "institution,field_of_study,degree_level,started_at,ended_at,is_ongoing",
            profile_id,
        ),
        _profile_rows(supabase, "languages", "name,proficiency", profile_id),
        _profile_rows(supabase, "certifications", "name,issuer,issued_at", profile_id),
    )
    return build_printable_cv(
        profile=profile,
        primary_cv=primary_cv,
        account_email=current_user.email or "",
        skills=skills,
        experiences=experiences,
        educations=educations,
        languages=languages,
        certifications=certifications,
    )


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

    completeness = await _update_completeness(supabase, str(profile["id"]))
    if completeness is not None:
        profile = {**profile, "completeness_pct": completeness}

    return MasterProfile.model_validate(profile)


@router.post("/documents", response_model=UploadedDocument, status_code=201)
async def create_profile_document(
    payload: UploadedDocumentCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> UploadedDocument:
    # El perfil y el archivo tienen que ser de quien llama: mismo 404 si el perfil no
    # existe o es ajeno, para no revelar ids de otras personas.
    profile = await _fetch_profile(supabase, current_user.id)
    if str(profile.get("id")) != payload.profile_id:
        raise _not_found()
    _ensure_own_storage_path(payload.storage_path, current_user.supabase_uid)
    # Antes de tocar el slot: un pedido bloqueado no puede borrar el CV que ya está.
    await _enforce_document_upload_limit(current_user)

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

    task_id = parsing_tasks.enqueue_parse_cv(str(document["id"]), current_user.id)
    document["task_id"] = task_id
    return UploadedDocument.model_validate(document)


@router.patch("/documents/{document_id}/set-primary", response_model=UploadedDocument)
async def set_primary_profile_document(
    document_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> UploadedDocument:
    try:
        response = await (
            supabase.rpc(
                "set_primary_uploaded_document",
                {"p_user_id": current_user.id, "p_document_id": document_id},
            )
            .execute()
        )
    except APIError as exc:
        # La función SQL levanta una excepción si el documento no existe, no es un CV o
        # es de otra persona: para quien pregunta es lo mismo, un 404. Cualquier otro
        # error (por ejemplo un id mal formado) sigue su camino habitual.
        if exc.code != RAISED_EXCEPTION:
            raise
        raise _document_not_found() from exc
    document = getattr(response, "data", None)
    if not isinstance(document, dict):
        raise _document_not_found()

    task_id = parsing_tasks.enqueue_parse_cv(document_id, current_user.id)
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
    storage_path = document.get("storage_path")
    await _remove_stored_files(supabase, [str(storage_path)] if storage_path else [])
    await _update_completeness(supabase, str(document["profile_id"]))


async def _matching_skill_rows(
    supabase: Any,
    profile_id: str,
    name: str,
    category: str | None,
) -> list[dict[str, Any]]:
    """Las skills del perfil con la misma clave que usa el parseo del CV."""
    wanted = normalize_skill_key(name, category)
    rows = await _profile_rows(
        supabase, "skills", "id,name,category,in_cv,confirmed", profile_id
    )
    return [
        row
        for row in rows
        if normalize_skill_key(str(row.get("name") or ""), row.get("category"))
        == wanted
    ]


async def _confirm_existing_skills(
    supabase: Any,
    rows: list[dict[str, Any]],
    payload: SkillCreate,
) -> dict[str, Any]:
    """Confirmar una skill que ya está guardada la actualiza, no agrega otra fila.

    El parseo del CV ya la guardó (con su vector) antes de que la persona la confirme
    en el paso 3: insertar de nuevo dejaba dos filas, la confirmada sin vector. Un alta
    nunca baja una marca que ya estaba puesta.
    """
    first: dict[str, Any] | None = None
    for row in rows:
        changes: dict[str, Any] = {
            "in_cv": bool(row.get("in_cv")) or payload.in_cv,
            "confirmed": bool(row.get("confirmed")) or payload.confirmed,
        }
        if payload.level is not None:
            changes["level"] = payload.level
        response = (
            await supabase.table("skills")
            .update(changes)
            .eq("id", row["id"])
            .execute()
        )
        data = getattr(response, "data", None)
        if first is None and isinstance(data, list) and data:
            first = dict(data[0])
    skill = first if first is not None else dict(rows[0])
    skill.pop("embedding", None)
    return skill


@router.post("/skills", status_code=201)
async def create_profile_skill(
    payload: SkillCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> dict[str, Any]:
    profile = await _fetch_profile(supabase, current_user.id)
    profile_id = str(profile["id"])
    matches = await _matching_skill_rows(
        supabase, profile_id, payload.name, payload.category
    )
    if matches:
        skill = await _confirm_existing_skills(supabase, matches, payload)
    else:
        skill = await _insert_profile_row(
            supabase,
            "skills",
            profile_id,
            {
                "name": payload.name,
                "category": payload.category,
                "level": payload.level,
                "in_cv": payload.in_cv,
                "confirmed": payload.confirmed,
            },
        )
    await _update_completeness(supabase, profile_id)
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


def _detail_not_found(label: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": f"{label} no encontrada", "code": code, "details": {}},
    )


async def _update_profile_row(
    supabase: Any,
    table_name: str,
    columns: str,
    profile_id: str,
    row_id: UUID,
    changes: dict[str, Any],
    not_found: HTTPException,
) -> dict[str, Any]:
    """Cambia una fila del perfil de quien pregunta.

    Filtra por el perfil además del id: una fila de otra persona responde igual que una
    inexistente (404) y no se toca.
    """
    table = supabase.table(table_name)
    query = table.update(changes) if changes else table.select(columns)
    response = await (
        query.eq("id", str(row_id)).eq("profile_id", profile_id).execute()
    )
    data = getattr(response, "data", None)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    raise not_found


@router.get("/details", response_model=ProfileDetails)
async def get_profile_details(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> ProfileDetails:
    """Experiencia, educación e idiomas cargados a mano: el paso 4 los muestra."""
    profile = await _fetch_profile(supabase, current_user.id)
    profile_id = str(profile["id"])
    experiences, educations, languages = await asyncio.gather(
        _profile_rows(
            supabase,
            "experiences",
            "id,company,title,description",
            profile_id,
            newest_first=True,
        ),
        _profile_rows(
            supabase,
            "educations",
            "id,institution,field_of_study,degree_level",
            profile_id,
            newest_first=True,
        ),
        _profile_rows(
            supabase,
            "languages",
            "id,name,proficiency",
            profile_id,
            newest_first=True,
        ),
    )
    return ProfileDetails(
        experiences=[ProfileExperienceItem(**row) for row in experiences],
        educations=[ProfileEducationItem(**row) for row in educations],
        languages=[
            ProfileLanguageItem(
                id=row["id"], name=row.get("name") or "", level=row.get("proficiency")
            )
            for row in languages
        ],
    )


@router.patch("/experiences/{experience_id}", response_model=ProfileExperienceItem)
async def update_profile_experience(
    experience_id: UUID,
    payload: ExperienceUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> ProfileExperienceItem:
    profile = await _fetch_profile(supabase, current_user.id)
    profile_id = str(profile["id"])
    row = await _update_profile_row(
        supabase,
        "experiences",
        "id,company,title,description",
        profile_id,
        experience_id,
        payload.to_update_payload(),
        _detail_not_found("Experiencia", "EXPERIENCE_NOT_FOUND"),
    )
    await _update_completeness(supabase, profile_id)
    return ProfileExperienceItem(**row)


@router.patch("/educations/{education_id}", response_model=ProfileEducationItem)
async def update_profile_education(
    education_id: UUID,
    payload: EducationUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> ProfileEducationItem:
    profile = await _fetch_profile(supabase, current_user.id)
    profile_id = str(profile["id"])
    row = await _update_profile_row(
        supabase,
        "educations",
        "id,institution,field_of_study,degree_level",
        profile_id,
        education_id,
        payload.to_update_payload(),
        _detail_not_found("Educación", "EDUCATION_NOT_FOUND"),
    )
    await _update_completeness(supabase, profile_id)
    return ProfileEducationItem(**row)


@router.patch("/languages/{language_id}", response_model=ProfileLanguageItem)
async def update_profile_language(
    language_id: UUID,
    payload: LanguageUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> ProfileLanguageItem:
    profile = await _fetch_profile(supabase, current_user.id)
    profile_id = str(profile["id"])
    row = await _update_profile_row(
        supabase,
        "languages",
        "id,name,proficiency",
        profile_id,
        language_id,
        payload.to_update_payload(),
        _detail_not_found("Idioma", "LANGUAGE_NOT_FOUND"),
    )
    await _update_completeness(supabase, profile_id)
    return ProfileLanguageItem(
        id=row["id"], name=row.get("name") or "", level=row.get("proficiency")
    )


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
