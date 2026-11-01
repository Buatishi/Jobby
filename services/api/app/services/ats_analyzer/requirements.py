"""Los requisitos duros del puesto contra lo que muestra la persona (Decisión 42).

Tres requisitos, todos deterministas y sin IA: años de experiencia directa, formación e
idiomas. Las skills ya se miden con las keywords del reporte.

Regla del autor (2026-10-31): no hace falta cumplir lo pedido al pie de la letra. Si la
persona lo **supera** (más años, un título más alto, un idioma mejor) el requisito se da
por cumplido por completo y se deja una nota aparte: no suma ni resta puntos.
"""

import re
from collections.abc import Iterable
from datetime import date
from typing import Any

from app.models.ats import ATSRequirement
from app.services.ats_analyzer.experience import (
    assess_roles,
    describe_months,
    direct_months,
    required_years,
)
from app.services.match_engine.common import clamp
from app.services.match_engine.s_languages import (
    DEFAULT_LEVEL,
    LANGUAGE_LEVEL,
    profile_language_levels,
    required_languages,
)
from app.services.text_quality import fold

# Cuánto falta para pasar de «cumple» a «no cumple» en cada requisito.
PARTIAL_FROM_YEARS = 0.5  # con la mitad de los años pedidos ya es parcial
_LEVEL_STEP = 0.25  # cada escalón que falta en un idioma o título resta un cuarto
EXCEEDS_MARGIN_MONTHS = 12  # más de un año sobre lo pedido se aclara en una nota

# Escalones de formación; el curso suelto no es una formación.
EDUCATION_LABEL = {
    0: "sin formación formal",
    1: "secundario",
    2: "técnico",
    3: "grado universitario",
    4: "posgrado o maestría",
    5: "doctorado",
}
_COURSE = re.compile(r"\b(cursos?|courses?|bootcamp|coursera|udemy|certificat\w*)\b")
_EDUCATION_RANKS: list[tuple[int, re.Pattern[str]]] = [
    (5, re.compile(r"\b(phd|doctorado|doctorate|doctoral)\b")),
    (
        4,
        re.compile(
            r"\b(master|maestria|magister|mba|posgrado|postgrado|postgraduate)\b"
        ),
    ),
    (
        3,
        re.compile(
            r"\b(bachelor|undergraduate|degree|licenciad\w*|licenciatura|lic|"
            r"ingenier\w*|universitari\w*|universidad|university|facultad|grado)\b"
        ),
    ),
    (2, re.compile(r"\b(tecnic\w*|tecnicatura|technical|associate|terciari\w*)\b")),
    (1, re.compile(r"\b(secundari\w*|bachiller|high school)\b")),
]
_EQUIVALENT = re.compile(r"equivalen")

LEVEL_LABEL = {1: "básico", 2: "intermedio", 3: "avanzado", 4: "nativo"}
LANGUAGE_LABEL = {
    "english": "Inglés",
    "spanish": "Español",
    "portuguese": "Portugués",
    "french": "Francés",
    "german": "Alemán",
    "italian": "Italiano",
}


def education_rank(text: str) -> int:
    """Escalón de formación que nombra un texto (0 si no nombra ninguno)."""
    folded = fold(text)
    for rank, pattern in _EDUCATION_RANKS:
        if pattern.search(folded):
            return rank
    return 0


def _education_text(row: dict[str, Any]) -> str:
    parts = (row.get("degree_level"), row.get("field_of_study"), row.get("institution"))
    return " ".join(str(part) for part in parts if part)


def _experience_requirement(
    job: dict[str, Any],
    experiences: Iterable[dict[str, Any]],
    today: date | None,
) -> ATSRequirement | None:
    years, estimated = required_years(job)
    if not years:
        return None

    roles = assess_roles(experiences, job, today)
    months = direct_months(roles)
    needed = years * 12
    ratio = clamp(months / needed)
    detail = [
        f"{role.label}: {describe_months(role.months)}"
        if role.counted
        else f"{role.label}: no cuenta ({role.reason})"
        for role in roles
    ]
    exceeds = months >= needed + EXCEEDS_MARGIN_MONTHS
    return ATSRequirement(
        key="experience",
        label="Experiencia directa",
        required=f"{years} años"
        + (" (según el nivel del puesto)" if estimated else ""),
        actual=describe_months(months),
        status="met"
        if ratio >= 1
        else "partial"
        if ratio >= PARTIAL_FROM_YEARS
        else "unmet",
        ratio=ratio,
        note=(
            f"Superás lo pedido ({describe_months(months)} contra {years} años): "
            "no suma ni resta puntos."
            if exceeds
            else None
        ),
        estimated=estimated,
        detail=detail,
    )


def _education_requirement(
    job: dict[str, Any], educations: Iterable[dict[str, Any]]
) -> ATSRequirement | None:
    required_text = str(job.get("required_education") or "").strip()
    if not required_text:
        return None
    needed = education_rank(required_text)
    if needed == 0:
        return None

    best_rank, best_row, ongoing_only = 0, None, True
    for row in educations:
        text = _education_text(row)
        rank = 0 if _COURSE.search(fold(text)) else education_rank(text)
        if rank == 0:
            continue
        ongoing = bool(row.get("is_ongoing"))
        # Un título terminado le gana a uno en curso del mismo escalón.
        if rank > best_rank or (rank == best_rank and ongoing_only and not ongoing):
            best_rank, best_row, ongoing_only = rank, row, ongoing

    flexible = bool(_EQUIVALENT.search(fold(required_text)))
    actual = EDUCATION_LABEL[best_rank]
    if best_row is not None:
        title = (
            best_row.get("field_of_study") or best_row.get("degree_level") or ""
        ).strip()
        actual = f"{actual} ({title})" if title else actual
        if ongoing_only:
            actual += ", en curso"

    note = None
    if best_rank >= needed and not ongoing_only:
        ratio = 1.0
        if best_rank > needed:
            note = "Superás lo pedido: no suma ni resta puntos."
    elif best_rank >= needed:  # alcanza el escalón, pero todavía no lo terminó
        ratio = 0.5
        note = "El título está en curso: cuenta a medias hasta que lo termines."
    else:
        ratio = clamp(1 - (needed - best_rank) * _LEVEL_STEP)
        if best_rank == 0:
            ratio = 0.0
    if ratio < 1 and flexible:
        ratio = max(ratio, 0.5)
        note = "El aviso acepta experiencia equivalente al título."
    return ATSRequirement(
        key="education",
        label="Formación",
        required=required_text,
        actual=actual,
        status="met" if ratio >= 1 else "partial" if ratio > 0 else "unmet",
        ratio=ratio,
        note=note,
    )


def _language_requirements(
    job: dict[str, Any], languages: Iterable[dict[str, Any]]
) -> list[ATSRequirement]:
    required = required_languages(job)
    if not required:
        return []
    levels = profile_language_levels(list(languages))
    results: list[ATSRequirement] = []
    seen: set[str] = set()
    for item in required:
        key = item["name"]
        if key in seen:
            continue
        seen.add(key)
        needed = LANGUAGE_LEVEL.get(item["level"], LANGUAGE_LEVEL[DEFAULT_LEVEL])
        has = levels.get(key)
        # El nivel por defecto es el que se supone cuando el aviso no dice nivel.
        asked = (
            "nivel no indicado"
            if item["level"] == DEFAULT_LEVEL
            else LEVEL_LABEL.get(needed, "")
        )
        if has is None:
            ratio, actual, note = 0.0, "no figura en tu perfil ni en tu CV", None
        else:
            ratio = 1.0 if has >= needed else clamp(1 - (needed - has) * _LEVEL_STEP)
            actual = LEVEL_LABEL.get(min(has, 4), "")
            note = (
                "Superás lo pedido: no suma ni resta puntos." if has > needed else None
            )
        results.append(
            ATSRequirement(
                key=f"language:{key}",
                label=LANGUAGE_LABEL.get(key, key.capitalize()),
                required=asked,
                actual=actual,
                status="met" if ratio >= 1 else "partial" if ratio > 0 else "unmet",
                ratio=ratio,
                note=note,
            )
        )
    return results


def evaluate_requirements(
    job: dict[str, Any],
    *,
    experiences: Iterable[dict[str, Any]],
    educations: Iterable[dict[str, Any]],
    languages: Iterable[dict[str, Any]],
    today: date | None = None,
) -> list[ATSRequirement]:
    """Los requisitos que el puesto pide y la persona puede mostrar, en orden fijo."""
    requirements = [
        _experience_requirement(job, experiences, today),
        _education_requirement(job, educations),
        *_language_requirements(job, languages),
    ]
    return [requirement for requirement in requirements if requirement is not None]
