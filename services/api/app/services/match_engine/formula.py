from dataclasses import dataclass
from typing import Any

from app.services.match_engine.common import clamp
from app.services.match_engine.s_company import compute_company_score
from app.services.match_engine.s_education import compute_education_score
from app.services.match_engine.s_languages import compute_languages_score
from app.services.match_engine.s_seniority import compute_seniority_score
from app.services.match_engine.s_skills import (
    compute_skills_score,
    required_skill_names,
)
from app.services.match_engine.s_soft import compute_soft_score


@dataclass(frozen=True)
class MatchResult:
    match_score: int
    potential_score: int
    representation_score: int
    gap_origin: str
    score_breakdown: dict[str, Any]


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


async def _fetch_list(db: Any, table_name: str, **filters: Any) -> list[dict[str, Any]]:
    query = db.table(table_name).select("*")
    for key, value in filters.items():
        query = query.eq(key, value)
    data = await _execute(query)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


async def _fetch_one(db: Any, table_name: str, **filters: Any) -> dict[str, Any]:
    query = db.table(table_name).select("*")
    for key, value in filters.items():
        query = query.eq(key, value)
    data = await _execute(query.maybe_single())
    if not isinstance(data, dict):
        raise ValueError(f"{table_name} row not found.")
    return data


async def _cache_soft_skills(
    db: Any,
    profile_id: str,
    profile: dict[str, Any],
    detected: list[str],
) -> None:
    if profile.get("inferred_soft_skills") == detected:
        return
    await _execute(
        db.table("master_profiles")
        .update({"inferred_soft_skills": detected})
        .eq("id", profile_id)
    )


def _weighted_score(scores: dict[str, float]) -> int:
    value = (
        scores["skills"] * 0.35
        + scores["seniority"] * 0.25
        + scores["education"] * 0.10
        + scores["languages"] * 0.10
        + scores["company"] * 0.15
        + scores["soft"] * 0.05
    )
    return round(clamp(value) * 100)


def _representation_score(
    profile_skills: list[dict[str, Any]],
    documents: list[dict[str, Any]],
) -> int:
    confirmed = [skill for skill in profile_skills if skill.get("confirmed")]
    if not confirmed:
        return 0

    primary_cv = next(
        (
            document
            for document in documents
            if document.get("type") == "cv" and document.get("is_primary")
        ),
        None,
    )
    parsed_skills = set()
    if primary_cv and isinstance(primary_cv.get("parsed_data"), dict):
        parsed = primary_cv["parsed_data"].get("skills") or []
        if isinstance(parsed, list):
            parsed_skills = {
                str(skill.get("name") if isinstance(skill, dict) else skill).lower()
                for skill in parsed
            }

    in_cv_count = sum(
        1
        for skill in confirmed
        if skill.get("in_cv") or str(skill.get("name", "")).lower() in parsed_skills
    )
    return round((in_cv_count / len(confirmed)) * 100)


def _gap_origin(skills_score: float, seniority_score: float) -> str:
    skill_gap = skills_score < 0.70
    seniority_gap = seniority_score < 0.70
    if skill_gap and seniority_gap:
        return "both"
    if skill_gap:
        return "skills"
    if seniority_gap:
        return "seniority"
    return "none"


async def compute_match_score(profile_id: str, job_id: str, db: Any) -> MatchResult:
    profile = await _fetch_one(db, "master_profiles", id=profile_id)
    job = await _fetch_one(db, "job_descriptions", id=job_id)
    profile_skills = await _fetch_list(db, "skills", profile_id=profile_id)
    educations = await _fetch_list(db, "educations", profile_id=profile_id)
    certifications = await _fetch_list(db, "certifications", profile_id=profile_id)
    languages = await _fetch_list(db, "languages", profile_id=profile_id)
    experiences = await _fetch_list(db, "experiences", profile_id=profile_id)
    documents = await _fetch_list(
        db,
        "uploaded_documents",
        profile_id=profile_id,
        user_id=profile["user_id"],
    )

    skills_result = compute_skills_score(profile_skills, job)
    seniority_score = compute_seniority_score(profile, job)
    education_score = compute_education_score(educations, certifications, job)
    languages_score = compute_languages_score(languages, job)
    company_result = compute_company_score(profile, profile_skills, job)
    soft_result = compute_soft_score(profile, experiences, job)
    await _cache_soft_skills(db, profile_id, profile, soft_result["detected"])

    scores = {
        "skills": float(skills_result["score"]),
        "seniority": seniority_score,
        "education": education_score,
        "languages": languages_score,
        "company": company_result["score"],
        "soft": soft_result["score"],
    }
    match_score = _weighted_score(scores)
    potential_scores = {**scores, "skills": 1.0}
    potential_score = max(match_score, _weighted_score(potential_scores))
    representation_score = _representation_score(profile_skills, documents)
    gap_origin = _gap_origin(scores["skills"], seniority_score)

    score_breakdown = {
        "sub_scores": scores,
        "skills": skills_result,
        "company": company_result,
        "soft": soft_result,
        "required_skills": required_skill_names(job),
    }
    return MatchResult(
        match_score=match_score,
        potential_score=potential_score,
        representation_score=representation_score,
        gap_origin=gap_origin,
        score_breakdown=score_breakdown,
    )
