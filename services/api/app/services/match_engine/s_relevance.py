"""Relevancia del puesto para el área de la persona.

El MatchScore mezcla seis componentes, y cuatro de ellos (seniority, idiomas,
empresa y blandas) valen entre 0,75 y 0,85 apenas el puesto no pide algo puntual,
sea cual sea el rubro. Sin esta compuerta un CV de sistemas contra un puesto
de chef sumaba ~52 puntos solo por «no pedir inglés» y por coincidir en la modalidad.

La relevancia mide cuánto del puesto cae en lo que la persona sabe hacer y multiplica
el puntaje: sin ninguna coincidencia queda en `RELEVANCE_FLOOR`; con
`FULL_RELEVANCE_AT` de las skills pedidas ya es del área y el puntaje no cambia.
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
FULL_RELEVANCE_AT = 0.4
# Cuando el puesto no lista skills: menciones de las skills de la persona en el texto
# del puesto con las que se lo considera de su área.
TEXT_MENTIONS_FOR_FULL = 4


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
        if len(name) < 2 or name in mentioned or not is_meaningful_name(name):
            continue
        # Palabra o frase completa: «sql» no cuenta dentro de «mysql».
        if re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", job_text):
            mentioned.add(name)
    return len(mentioned)


def compute_relevance(
    profile_skills: list[dict[str, Any]],
    job: dict[str, Any],
    skills_result: dict[str, Any],
) -> dict[str, Any]:
    if required_skill_names(job):
        evidence = float(skills_result["score"])
        source = "skills"
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
