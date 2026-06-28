from typing import Any

from app.services.match_engine.common import (
    clamp,
    count_semantic_matches,
    normalize_text,
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
    job_skills = _job_required_skill_items(job)
    if not job_skills:
        return {
            "score": 0.8,
            "literal_hits": [],
            "semantic_hits": 0,
            "missing_skills": [],
        }

    profile_by_name = {
        normalize_text(skill.get("name")): skill
        for skill in profile_skills
        if normalize_text(skill.get("name"))
    }
    job_names = required_skill_names(job)
    literal_hits = sorted(set(profile_by_name).intersection(job_names))
    literal_score = len(literal_hits) / len(job_names)

    unmatched_profile = [
        skill
        for name, skill in profile_by_name.items()
        if name not in literal_hits and skill.get("embedding") is not None
    ]
    unmatched_job = [
        skill
        for skill in job_skills
        if normalize_text(skill.get("name")) not in literal_hits
        and skill.get("embedding") is not None
    ]
    semantic_hits = count_semantic_matches(
        unmatched_profile,
        unmatched_job,
        threshold=semantic_threshold,
    )
    semantic_score = (semantic_hits * 0.6) / len(job_names)
    missing_count = max(0, len(job_names) - len(literal_hits) - semantic_hits)

    return {
        "score": clamp(literal_score + semantic_score),
        "literal_hits": literal_hits,
        "semantic_hits": semantic_hits,
        "missing_skills": job_names[-missing_count:] if missing_count else [],
    }
