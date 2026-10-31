"""Relevancia del puesto para el área de la persona.

El MatchScore mezcla seis componentes, y cuatro de ellos (seniority, idiomas,
empresa y blandas) valen entre 0,75 y 0,85 apenas el puesto no pide algo puntual,
sea cual sea el rubro. Sin esta compuerta un CV de sistemas contra un puesto
de chef sumaba ~52 puntos solo por «no pedir inglés» y por coincidir en la modalidad.

La relevancia mide cuánto del puesto cae en lo que la persona sabe hacer y multiplica
el puntaje: sin ninguna coincidencia queda en `RELEVANCE_FLOOR`; con
`FULL_RELEVANCE_AT` de las skills pedidas ya es del área y el puntaje no cambia.

Una skill pedida cuenta si está en las filas de `skills` o si el perfil la nombra
(headline, rol, bio, cargos y logros). Con solo las filas, quien tiene pocas skills
cargadas pero las nombra en su bio parecía de otra área: un puesto de su propio rubro
perdía la mitad del puntaje.
"""

import re
from typing import Any

from app.services.match_engine.common import clamp, normalize_text
from app.services.match_engine.s_skills import required_skill_names
from app.services.text_quality import fold, is_meaningful_name

# Piso: una coincidencia nula no baja el puntaje a 0 para que siga siendo comparable
# entre puestos y porque la extracción de skills del puesto puede fallar.
RELEVANCE_FLOOR = 0.15
# Fracción de las skills pedidas con la que el puesto se considera de la misma área.
# Era 0,4; con el stack y las skills limpias (Decisión 39) un puesto con muchas
# tecnologías pedía tener 8 de 20 para no atenuarse. Ver la Actualización de la
# Decisión 29 del 2026-10-30.
FULL_RELEVANCE_AT = 0.25
# Cuando el puesto no lista skills: menciones de las skills de la persona en el texto
# del puesto con las que se lo considera de su área.
TEXT_MENTIONS_FOR_FULL = 4


def build_profile_text(
    profile: dict[str, Any],
    profile_skills: list[dict[str, Any]],
    experiences: list[dict[str, Any]],
) -> str:
    """Todo lo que la persona dice de sí misma, para buscar en él las skills pedidas."""
    parts: list[Any] = [
        profile.get("headline"),
        profile.get("target_role"),
        profile.get("summary"),
    ]
    parts.extend(skill.get("name") for skill in profile_skills)
    for experience in experiences:
        parts.append(experience.get("title"))
        parts.append(experience.get("description"))
        achievements = experience.get("achievements")
        if isinstance(achievements, list):
            parts.extend(achievements)
    return fold(" ".join(str(part) for part in parts if part))


def _mentions(text: str, term: str) -> bool:
    """Palabra o frase completa: «sql» no cuenta dentro de «mysql»."""
    if len(term) < 2:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def _job_text(job: dict[str, Any]) -> str:
    parts = [
        job.get("job_title"),
        job.get("raw_text"),
        " ".join(str(item) for item in job.get("tech_stack") or []),
    ]
    return fold(" ".join(str(part) for part in parts if part))


def _mentioned_skills(profile_skills: list[dict[str, Any]], job_text: str) -> int:
    mentioned: set[str] = set()
    for skill in profile_skills:
        name = fold(str(skill.get("name") or ""))
        if name in mentioned or not is_meaningful_name(name):
            continue
        if _mentions(job_text, name):
            mentioned.add(name)
    return len(mentioned)


def _named_required_skills(required: list[str], profile_text: str) -> float:
    names = {fold(name) for name in required}
    names.discard("")
    if not names or not profile_text:
        return 0.0
    return sum(_mentions(profile_text, name) for name in names) / len(names)


def compute_relevance(
    profile_skills: list[dict[str, Any]],
    job: dict[str, Any],
    skills_result: dict[str, Any],
    profile_text: str = "",
) -> dict[str, Any]:
    required = required_skill_names(job)
    if required:
        from_rows = float(skills_result["score"])
        from_text = _named_required_skills(required, profile_text)
        evidence = max(from_rows, from_text)
        source = "skills" if from_rows >= from_text else "profile_text"
    else:
        text = _job_text(job)
        if not normalize_text(text):
            # Sin skills ni texto no hay con qué juzgar el área: no se castiga.
            return {"score": 1.0, "evidence": None, "source": "none"}
        mentions = _mentioned_skills(profile_skills, text)
        evidence = clamp(mentions / TEXT_MENTIONS_FOR_FULL)
        source = "text"

    scaled = clamp(evidence / FULL_RELEVANCE_AT)
    return {
        "score": RELEVANCE_FLOOR + (1 - RELEVANCE_FLOOR) * scaled,
        "evidence": evidence,
        "source": source,
    }
