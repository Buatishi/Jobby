import re
from typing import Any

from app.services.match_engine.common import (
    clamp,
    normalize_text,
    semantic_match_indexes,
    skill_key,
)
from app.services.skill_filter import skill_keywords

# «Relational databases (MySQL or similar)» pide «Relational databases»: lo que va entre
# paréntesis aclara o enumera y no es parte del nombre de la skill.
_PARENTHETICAL = re.compile(r"\s*\([^)]*\)")


def _raw_required_skill_items(job: dict[str, Any]) -> list[dict[str, Any]]:
    fallback_embedding = job.get("embedding")
    required_skills = job.get("required_skills")
    if isinstance(required_skills, list):
        return [
            {"name": str(skill), "embedding": fallback_embedding}
            if not isinstance(skill, dict)
            else {**skill, "embedding": skill.get("embedding", fallback_embedding)}
            for skill in required_skills
        ]
    if isinstance(required_skills, dict):
        values = required_skills.get("skills", required_skills.get("required"))
        if isinstance(values, list):
            return [
                {"name": str(skill), "embedding": fallback_embedding}
                if not isinstance(skill, dict)
                else {**skill, "embedding": skill.get("embedding", fallback_embedding)}
                for skill in values
            ]
    return []


def _tech_stack_items(job: dict[str, Any]) -> list[dict[str, Any]]:
    fallback_embedding = job.get("embedding")
    tech_stack = job.get("tech_stack")
    if not isinstance(tech_stack, list):
        return []
    return [{"name": str(tech), "embedding": fallback_embedding} for tech in tech_stack]


def _clean_skill_items(
    items: list[dict[str, Any]], job: dict[str, Any]
) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        name = _PARENTHETICAL.sub("", str(item.get("name") or "")).strip()
        if not skill_keywords([name], job) or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        cleaned.append({**item, "name": name})
    return cleaned


def _job_required_skill_items(job: dict[str, Any]) -> list[dict[str, Any]]:
    """Las skills que pide el puesto, como nombres y no como tareas (Decisión 39).

    La IA que lee el aviso devuelve en `required_skills` frases como «Optimizing
    sessions, events, latency, turns, interruptions and error fallbacks»: ninguna skill
    del perfil se llama así, así que cada una sumaba al divisor sin poder coincidir
    jamás. Se les saca el paréntesis, se descartan las que no son una habilidad (frases
    de más de 5 palabras, nivel, modalidad, título; ver `skill_filter`) y se cuenta una
    sola vez el mismo nombre. Dos alias distintos («REST API» y «API REST») siguen
    contando cada uno.

    El `tech_stack` del puesto también se pide: la IA suele dejar ahí «Python» y no en
    `required_skills`. Se suma lo que no esté ya (por forma común, `skill_key`: «API
    REST» y «REST APIs» son la misma) y pasa por la misma limpieza.

    Si no queda ninguna, se conserva `required_skills` tal como vino: una lista vacía se
    leería como «el puesto no pide nada» y daría el puntaje neutro (0,8) en lugar de 0.
    """
    items = _raw_required_skill_items(job)
    required = _clean_skill_items(items, job)
    known = {skill_key(item["name"]) for item in required}
    for item in _clean_skill_items(_tech_stack_items(job), job):
        key = skill_key(item["name"])
        if key not in known:
            known.add(key)
            required.append(item)
    return required or items


def required_skill_names(job: dict[str, Any]) -> list[str]:
    return [
        normalize_text(skill.get("name"))
        for skill in _job_required_skill_items(job)
        if normalize_text(skill.get("name"))
    ]


def compute_skills_score(
    profile_skills: list[dict[str, Any]],
    job: dict[str, Any],
    semantic_threshold: float = 0.82,
) -> dict[str, Any]:
    job_skills = [
        skill
        for skill in _job_required_skill_items(job)
        if normalize_text(skill.get("name"))
    ]
    if not job_skills:
        return {
            "score": 0.8,
            "literal_hits": [],
            "semantic_hits": 0,
            "missing_skills": [],
        }

    # Se compara por forma común (`skill_key`): «API REST» es «REST APIs».
    profile_by_key = {
        skill_key(skill.get("name")): skill
        for skill in profile_skills
        if skill_key(skill.get("name"))
    }
    job_keys = [skill_key(skill.get("name")) for skill in job_skills]
    is_literal = [key in profile_by_key for key in job_keys]
    # Cada skill pedida cuenta: con alias el puesto puede repetir una con dos
    # nombres ("REST API" y "API REST") y las dos coinciden.
    literal_score = sum(is_literal) / len(job_skills)
    literal_hits = sorted(
        {
            normalize_text(skill.get("name"))
            for skill, hit in zip(job_skills, is_literal, strict=True)
            if hit
        }
    )

    used_keys = {key for key, hit in zip(job_keys, is_literal, strict=True) if hit}
    unmatched_profile = [
        skill
        for key, skill in profile_by_key.items()
        if key not in used_keys and skill.get("embedding") is not None
    ]
    pending = [
        index
        for index, skill in enumerate(job_skills)
        if not is_literal[index] and skill.get("embedding") is not None
    ]
    matched = semantic_match_indexes(
        unmatched_profile,
        [job_skills[index] for index in pending],
        threshold=semantic_threshold,
    )
    semantic_jobs = {pending[position] for position in matched}
    semantic_score = (len(semantic_jobs) * 0.6) / len(job_skills)

    return {
        "score": clamp(literal_score + semantic_score),
        "literal_hits": literal_hits,
        "semantic_hits": len(semantic_jobs),
        # Las que de verdad faltan, en el orden del puesto. Antes se tomaban las
        # últimas N del puesto y figuraba como faltante una que la persona tiene.
        "missing_skills": [
            normalize_text(skill.get("name"))
            for index, skill in enumerate(job_skills)
            if not is_literal[index] and index not in semantic_jobs
        ],
    }
