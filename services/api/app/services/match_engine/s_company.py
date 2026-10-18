from typing import Any

from app.services.match_engine.common import (
    clamp,
    cosine_similarity,
    count_semantic_matches,
    normalize_text,
    skill_key,
)

MODALITY_COMPAT = {
    ("remote", "remote"): 1.00,
    ("hybrid", "hybrid"): 1.00,
    ("onsite", "onsite"): 1.00,
    ("remote", "hybrid"): 0.70,
    ("hybrid", "remote"): 0.85,
    ("hybrid", "onsite"): 0.60,
    ("onsite", "hybrid"): 0.60,
    ("remote", "onsite"): 0.20,
    ("onsite", "remote"): 0.20,
}


def compute_company_score(
    profile: dict[str, Any],
    profile_skills: list[dict[str, Any]],
    job: dict[str, Any],
) -> dict[str, float]:
    profile_tech = [
        skill
        for skill in profile_skills
        if normalize_text(skill.get("category")) == "technical"
    ]
    # Por forma común: «API REST» es «REST APIs» (ver `skill_key`).
    profile_names = {
        skill_key(skill.get("name")): skill
        for skill in profile_tech
        if skill_key(skill.get("name"))
    }
    job_tech_names = [normalize_text(item) for item in job.get("tech_stack") or []]
    job_tech = [
        {"name": item, "embedding": job.get("embedding")}
        for item in job_tech_names
    ]

    if not job_tech_names:
        tech_score = 0.8
    else:
        job_keys = [skill_key(name) for name in job_tech_names]
        is_literal = [key in profile_names for key in job_keys]
        literal_score = sum(is_literal) / len(job_tech_names)
        used_keys = {
            key for key, hit in zip(job_keys, is_literal, strict=True) if hit
        }
        semantic_hits = count_semantic_matches(
            [
                skill
                for name, skill in profile_names.items()
                if name not in used_keys and skill.get("embedding") is not None
            ],
            [
                skill
                for skill, hit in zip(job_tech, is_literal, strict=True)
                if not hit and skill.get("embedding") is not None
            ],
            threshold=0.82,
        )
        semantic_score = (semantic_hits * 0.6) / len(job_tech_names)
        tech_score = clamp(literal_score + semantic_score)

    user_pref = normalize_text(profile.get("work_modality")) or "hybrid"
    job_mode = normalize_text(job.get("required_modality")) or "hybrid"
    modality_score = MODALITY_COMPAT.get((user_pref, job_mode), 0.50)

    target_industry = profile.get("target_industry") or []
    if not target_industry or not job.get("industry"):
        industry_score = 0.70
    else:
        industry_score = clamp(
            cosine_similarity(profile.get("embedding"), job.get("embedding")) * 1.3
        )

    return {
        "score": tech_score * 0.50 + modality_score * 0.30 + industry_score * 0.20,
        "tech_score": tech_score,
        "modality_score": modality_score,
        "industry_score": industry_score,
    }
