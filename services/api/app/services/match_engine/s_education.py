from typing import Any

from app.services.match_engine.common import clamp, cosine_similarity

DEGREE_WEIGHT = {
    "phd": 1.00,
    "master": 0.90,
    "bachelor": 0.75,
    "associate": 0.55,
    "technical": 0.50,
    "course": 0.25,
    "none": 0.00,
}


def compute_education_score(
    educations: list[dict[str, Any]],
    certifications: list[dict[str, Any]],
    job: dict[str, Any],
) -> float:
    if not educations:
        cert_bonus = min(len(certifications) * 0.05, 0.15)
        return clamp(cert_bonus)

    best_score = 0.0
    for education in educations:
        spec_score = 0.3 + cosine_similarity(
            education.get("embedding"),
            job.get("embedding"),
        ) * 0.7
        level_score = DEGREE_WEIGHT.get(str(education.get("degree_level")), 0.25)
        if not job.get("required_education"):
            level_score = level_score * 0.5

        cert_bonus = min(len(certifications) * 0.05, 0.15)
        ongoing_bonus = 0.05 if education.get("is_ongoing") else 0.0
        continuing_bonus = min(cert_bonus + ongoing_bonus, 0.20)
        score = spec_score * 0.50 + level_score * 0.30 + continuing_bonus
        best_score = max(best_score, score)

    return clamp(best_score)
