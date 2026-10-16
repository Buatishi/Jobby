"""Porcentaje de perfil completo (0 a 100) que habilita el análisis de puestos.

Reemplaza a la función SQL `compute_completeness` (migraciones 014 y 020): la base
solo contaba que hubiera algo, así que «asdf» en el headline sumaba lo mismo que un
cargo real. Acá cada criterio exige además que el dato sirva para comparar el perfil
con un puesto. Los pesos son los mismos de antes y siguen sumando 100.

El valor se calcula y se guarda en `master_profiles.completeness_pct` en un solo
lugar (`refresh_completeness`); la función SQL devolvía el número pero no lo escribía.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

from app.services.match_engine.s_company import MODALITY_COMPAT
from app.services.match_engine.s_seniority import SENIORITY_ORDER
from app.services.text_quality import (
    fold,
    is_linkedin_profile_url,
    is_meaningful_name,
    is_meaningful_text,
)

WEIGHTS: dict[str, int] = {
    "headline": 8,
    "summary": 8,
    "target_role": 5,
    "target_seniority": 4,
    "work_modality": 3,
    "experience": 12,
    "skills": 10,
    "education": 8,
    "languages": 4,
    "cv": 20,
    "linkedin_document": 12,
    "linkedin_url": 6,
}

# La bio tiene que decir algo: con menos palabras útiles no hay qué comparar.
SUMMARY_MIN_WORDS = 5
SUMMARY_MIN_DIVERSITY = 0.6
MIN_CONFIRMED_SKILLS = 3
# Skills con nombre válido que salieron del documento para darlo por bien leído.
MIN_PARSED_SKILLS = 3

VALID_MODALITIES = frozenset(preference for preference, _ in MODALITY_COMPAT)
VALID_SENIORITIES = frozenset(SENIORITY_ORDER)


@dataclass(frozen=True)
class CompletenessResult:
    score: int
    points: dict[str, int]


def _text(row: dict[str, Any], key: str) -> str | None:
    value = row.get(key)
    return value if isinstance(value, str) else None


def _skill_names(skills: list[dict[str, Any]], *, confirmed_only: bool) -> set[str]:
    """Nombres distintos y con contenido: «Python» y «python » cuentan una sola vez."""
    names: set[str] = set()
    for skill in skills:
        name = _text(skill, "name")
        if confirmed_only and skill.get("confirmed") is not True:
            continue
        if name is not None and is_meaningful_name(name):
            names.add(fold(name))
    return names


def _parsed_document_points(
    documents: list[dict[str, Any]],
    doc_type: str,
    weight: int,
    parsed_skills: int,
    parsed_rows: int,
) -> int:
    """Puntos de un documento procesado, completos solo si dejó datos útiles.

    El parseo marca `done` aunque el PDF sea una imagen o salga ruido. Lo que importa
    para comparar es lo que quedó guardado, no que la tarea haya terminado: si no dejó
    ninguna skill ni ninguna fila, el documento no aporta.
    """
    if not any(
        document.get("type") == doc_type and document.get("status") == "done"
        for document in documents
    ):
        return 0
    if parsed_skills >= MIN_PARSED_SKILLS:
        return weight
    if parsed_skills >= 1 or parsed_rows >= 1:
        return weight // 2
    return 0


def compute_completeness(
    profile: dict[str, Any],
    experiences: list[dict[str, Any]],
    skills: list[dict[str, Any]],
    educations: list[dict[str, Any]],
    languages: list[dict[str, Any]],
    documents: list[dict[str, Any]],
) -> CompletenessResult:
    headline = _text(profile, "headline")
    summary = _text(profile, "summary")
    seniority = fold(_text(profile, "target_seniority") or "")
    modality = fold(_text(profile, "work_modality") or "")

    has_experience = any(
        is_meaningful_text(_text(row, "title"))
        and is_meaningful_name(_text(row, "company"))
        for row in experiences
    )
    # La UI del asistente guarda la educación como `institution` y deja la carrera
    # vacía: alcanza con que uno de los dos campos tenga contenido.
    has_education = any(
        is_meaningful_name(_text(row, "institution"))
        or is_meaningful_text(_text(row, "field_of_study"))
        for row in educations
    )
    has_language = any(is_meaningful_name(_text(row, "name")) for row in languages)

    in_cv_skills = _skill_names(
        [skill for skill in skills if skill.get("in_cv") is True],
        confirmed_only=False,
    )
    # Las skills que el PDF de LinkedIn nombró: no se agregan al perfil, solo se
    # marcan las que la persona ya tenía (`in_linkedin`).
    in_linkedin_skills = _skill_names(
        [skill for skill in skills if skill.get("in_linkedin") is True],
        confirmed_only=False,
    )
    parsed_rows = int(has_experience) + int(has_education)

    points = {
        "headline": WEIGHTS["headline"] if is_meaningful_text(headline) else 0,
        "summary": WEIGHTS["summary"]
        if is_meaningful_text(
            summary,
            min_words=SUMMARY_MIN_WORDS,
            min_diversity=SUMMARY_MIN_DIVERSITY,
        )
        and fold(summary or "") != fold(headline or "")
        else 0,
        "target_role": WEIGHTS["target_role"]
        if is_meaningful_text(_text(profile, "target_role"))
        else 0,
        "target_seniority": WEIGHTS["target_seniority"]
        if seniority in VALID_SENIORITIES
        else 0,
        "work_modality": WEIGHTS["work_modality"]
        if modality in VALID_MODALITIES
        else 0,
        "experience": WEIGHTS["experience"] if has_experience else 0,
        "skills": WEIGHTS["skills"]
        if len(_skill_names(skills, confirmed_only=True)) >= MIN_CONFIRMED_SKILLS
        else 0,
        "education": WEIGHTS["education"] if has_education else 0,
        "languages": WEIGHTS["languages"] if has_language else 0,
        "cv": _parsed_document_points(
            documents, "cv", WEIGHTS["cv"], len(in_cv_skills), parsed_rows
        ),
        "linkedin_document": _parsed_document_points(
            documents,
            "linkedin",
            WEIGHTS["linkedin_document"],
            len(in_linkedin_skills),
            parsed_rows,
        ),
        "linkedin_url": WEIGHTS["linkedin_url"]
        if is_linkedin_profile_url(_text(profile, "linkedin_url"))
        else 0,
    }
    return CompletenessResult(score=min(sum(points.values()), 100), points=points)


async def _rows(
    supabase: Any, table: str, columns: str, profile_id: str
) -> list[dict[str, Any]]:
    # Solo las columnas que se evalúan: `skills` guarda un vector de 1536 números por
    # fila y `uploaded_documents.parsed_data` llega a decenas de KB.
    query = supabase.table(table).select(columns).eq("profile_id", profile_id)
    response = await query.execute()
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


async def refresh_completeness(supabase: Any, profile_id: str) -> int:
    """Calcula el porcentaje con los datos actuales y lo guarda en el perfil."""
    profile_response = (
        await supabase.table("master_profiles")
        .select(
            "headline,summary,target_role,target_seniority,work_modality,linkedin_url"
        )
        .eq("id", profile_id)
        .maybe_single()
        .execute()
    )
    profile = getattr(profile_response, "data", None)
    if not isinstance(profile, dict):
        raise ValueError(f"Profile {profile_id} not found.")

    experiences, skills, educations, languages, documents = await asyncio.gather(
        _rows(supabase, "experiences", "title,company", profile_id),
        _rows(supabase, "skills", "name,confirmed,in_cv,in_linkedin", profile_id),
        _rows(supabase, "educations", "institution,field_of_study", profile_id),
        _rows(supabase, "languages", "name", profile_id),
        _rows(supabase, "uploaded_documents", "type,status", profile_id),
    )
    result = compute_completeness(
        profile, experiences, skills, educations, languages, documents
    )
    await (
        supabase.table("master_profiles")
        .update({"completeness_pct": result.score})
        .eq("id", profile_id)
        .execute()
    )
    return result.score
