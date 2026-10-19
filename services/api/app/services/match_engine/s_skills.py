from typing import Any

from app.services.match_engine.common import (
    clamp,
    normalize_text,
    semantic_match_indexes,
    skill_key,
)


def _job_required_skill_items(job: dict[str, Any]) -> list[dict[str, Any]]:
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
