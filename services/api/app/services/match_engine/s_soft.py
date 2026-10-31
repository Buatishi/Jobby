"""Habilidades blandas: lo que pide el puesto contra lo que cuenta el CV (Decisión 40).

El motor conoce diez habilidades (`SOFT_SKILL_SIGNALS`). Dos lados la traducen a ellas:

- El puesto escribe las suyas en texto libre, en español o en inglés («Teamwork»,
  «Trabajo en equipo», «Ganas de resolver problemas»). Antes solo contaban las que se
  llamaban igual que una de las diez, en inglés y de una palabra: de 29 pedidas en 7
  puestos guardados, 3 podían coincidir alguna vez, y el puntaje daba 0 con cualquier
  CV. Ahora cada frase se lleva a las habilidades que nombra (`SOFT_SKILL_ALIASES`) y la
  que no nombra ninguna no cuenta, ni a favor ni en contra.
- El CV las dice con otras palabras y con acentos: «Resolución de incidencias»,
  «Trabajo colaborativo», «Lideré». Se buscan sin acentos y por raíz al empezar una
  palabra: «comunic» sirve para «comunicación» y no para «telecomunicaciones».
"""

import re
from typing import Any

from app.services.match_engine.common import clamp
from app.services.text_quality import fold

# Raíces con las que el CV muestra cada habilidad, sin acentos y en minúscula.
SOFT_SKILL_SIGNALS = {
    "leadership": [
        "led", "lead", "managed", "directed", "lider", "dirig", "supervis",
        "gestion", "coordin",
    ],
    "communication": [
        "presented", "documented", "wrote", "present", "document",
        "comunic", "communicat",
    ],
    "ownership": [
        "owned", "ownership", "drove", "responsible for", "responsab", "a cargo",
    ],
    "collaboration": [
        "collaborat", "partnered", "teamwork", "colabor", "en conjunto",
        "trabajo en equipo", "trabajo colaborativo", "trabajo conjunto",
    ],
    "problem_solving": [
        "solved", "debugged", "resolv", "solucion", "resoluc",
        "troubleshoot", "problem solving",
    ],
    "analytical": [
        "analyzed", "measured", "evaluated", "analic", "evalu", "analiz",
        "analis", "analys",
    ],
    "initiative": [
        "proposed", "launched", "created", "propuse", "lanc", "lanz",
        "iniciativ", "initiative",
    ],
    "adaptability": [
        "migrated", "adapted", "learned", "migr", "aprend", "adapt", "flexib",
    ],
    "delivery": [
        "delivered", "shipped", "deployed", "entregu", "lanc", "entrega",
        "despleg", "deploy",
    ],
    "impact": ["%", "reduced", "increased", "improved", "reduje", "aument", "impact"],
}  # fmt: skip

# Raíces con las que un puesto nombra cada habilidad en lo que pide, sin acentos.
SOFT_SKILL_ALIASES = {
    "leadership": ["lead", "lider"],
    "communication": ["communicat", "comunic"],
    "ownership": ["ownership", "autonom", "responsab", "accountab"],
    "collaboration": [
        "collaborat", "colabor", "teamwork", "team work", "partnership",
        "trabajo en equipo", "trabajo colaborativo",
    ],
    "problem_solving": ["problem", "resoluc", "troubleshoot"],
    "analytical": ["analytic", "analitic", "analis", "analiz"],
    "initiative": ["initiative", "iniciativ", "proactiv", "self starter"],
    "adaptability": ["adapt", "flexib", "learn", "aprend"],
    "delivery": ["deliver", "entrega"],
    "impact": ["impact"],
}  # fmt: skip

_NOT_ALPHANUMERIC = re.compile(r"[^a-z0-9%]+")


def _pattern(stems: list[str]) -> re.Pattern[str]:
    """Una raíz coincide al empezar una palabra: «lanc» no está en «balance»."""
    return re.compile(
        "|".join(
            (r"(?<![a-z0-9])" if stem[0].isalnum() else "") + re.escape(stem)
            for stem in stems
        )
    )


_SIGNAL_PATTERNS = {key: _pattern(stems) for key, stems in SOFT_SKILL_SIGNALS.items()}
_ALIAS_PATTERNS = {key: _pattern(stems) for key, stems in SOFT_SKILL_ALIASES.items()}


def infer_soft_skills(experiences: list[dict[str, Any]]) -> list[str]:
    text_parts: list[str] = []
    for experience in experiences:
        achievements = experience.get("achievements") or []
        if isinstance(achievements, list):
            text_parts.extend(str(item) for item in achievements)
        text_parts.append(str(experience.get("description") or ""))

    text = fold(" ".join(text_parts))
    return sorted(
        skill for skill, pattern in _SIGNAL_PATTERNS.items() if pattern.search(text)
    )


def required_soft_skills(job: dict[str, Any]) -> list[frozenset[str]]:
    """Las habilidades que nombra cada frase del puesto; las que no nombran ninguna, no.

    Una frase que nombra dos («Autonomy to research and solve problems») cuenta una sola
    vez y se cumple con cualquiera de las dos.
    """
    required: list[frozenset[str]] = []
    for phrase in job.get("soft_skills") or []:
        text = _NOT_ALPHANUMERIC.sub(" ", fold(str(phrase)))
        named = frozenset(
            key for key, pattern in _ALIAS_PATTERNS.items() if pattern.search(text)
        )
        if named:
            required.append(named)
    return required


def compute_soft_score(
    profile: dict[str, Any],
    experiences: list[dict[str, Any]],
    job: dict[str, Any],
) -> dict[str, Any]:
    cached = list(profile.get("inferred_soft_skills") or [])
    required = required_soft_skills(job)
    if not required:
        # Sin nada que medir no se castiga: es el mismo 0,75 de un puesto que no pide.
        return {"score": 0.75, "detected": cached}

    # Lo que dice el CV hoy manda; lo guardado solo sirve si el CV no dice nada, para no
    # arrastrar una lectura vieja que no vio lo que ahora se reconoce.
    detected = set(infer_soft_skills(experiences)) or set(cached)

    matched = sum(1 for named in required if named & detected)
    base = matched / len(required)
    bonus = min(max(0, len(detected) - len(required)) * 0.03, 0.10)
    return {"score": clamp(base + bonus), "detected": sorted(detected)}
