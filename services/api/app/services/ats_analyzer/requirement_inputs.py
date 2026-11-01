"""De dónde salen los datos de la persona para los requisitos del puesto (Decisión 42).

Se juntan las tres fuentes que la persona tiene: lo que cargó a mano en el perfil, lo
que leyó su CV principal y lo que leyó su PDF de LinkedIn. Los puestos que están en
más de una fuente no se cuentan dos veces: los años se miden por meses y un mismo mes
cuenta una vez.

Todo es opcional para el reporte: si una lectura falla, esa fuente queda vacía y el
requisito se evalúa con lo que haya.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RequirementInputs:
    experiences: list[dict[str, Any]] = field(default_factory=list)
    educations: list[dict[str, Any]] = field(default_factory=list)
    languages: list[dict[str, Any]] = field(default_factory=list)


async def _rows(
    supabase: Any, table: str, columns: str, profile_id: str
) -> list[dict[str, Any]]:
    try:
        response = await (
            supabase.table(table).select(columns).eq("profile_id", profile_id).execute()
        )
    except Exception as exc:
        logger.warning("No se pudo leer %s para los requisitos: %s", table, exc)
        return []
    data = getattr(response, "data", None)
    return (
        [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []
    )


async def _profile_id(supabase: Any, user_id: str) -> str | None:
    try:
        response = await (
            supabase.table("master_profiles")
            .select("id")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.warning("No se pudo leer el perfil para los requisitos: %s", exc)
        return None
    data = getattr(response, "data", None)
    return str(data["id"]) if isinstance(data, dict) and data.get("id") else None


async def _linkedin_parsed(supabase: Any, profile_id: str) -> dict[str, Any]:
    try:
        response = await (
            supabase.table("uploaded_documents")
            .select("parsed_data")
            .eq("profile_id", profile_id)
            .eq("type", "linkedin")
            .eq("status", "done")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "No se pudo leer el PDF de LinkedIn para los requisitos: %s", exc
        )
        return {}
    data = getattr(response, "data", None)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        parsed = data[0].get("parsed_data")
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _items(parsed: Any, key: str) -> list[dict[str, Any]]:
    value = parsed.get(key) if isinstance(parsed, dict) else None
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


async def fetch_requirement_inputs(
    supabase: Any, user_id: str, primary_cv: dict[str, Any]
) -> RequirementInputs:
    """Experiencias, estudios e idiomas de la persona, de todas sus fuentes."""
    cv = primary_cv.get("parsed_data")
    inputs = RequirementInputs(
        experiences=_items(cv, "experiences"),
        educations=_items(cv, "educations"),
        languages=_items(cv, "languages"),
    )

    profile_id = await _profile_id(supabase, user_id)
    if profile_id is None:
        return inputs

    rows, linkedin = await asyncio.gather(
        asyncio.gather(
            _rows(
                supabase,
                "experiences",
                "company,title,started_at,ended_at,is_current,description,achievements",
                profile_id,
            ),
            _rows(
                supabase,
                "educations",
                "institution,field_of_study,degree_level,is_ongoing",
                profile_id,
            ),
            _rows(supabase, "languages", "name,proficiency", profile_id),
        ),
        _linkedin_parsed(supabase, profile_id),
    )
    experiences, educations, languages = rows
    inputs.experiences = [
        *experiences,
        *inputs.experiences,
        *_items(linkedin, "experiences"),
    ]
    inputs.educations = [
        *educations,
        *inputs.educations,
        *_items(linkedin, "educations"),
    ]
    inputs.languages = [*languages, *inputs.languages, *_items(linkedin, "languages")]
    return inputs
