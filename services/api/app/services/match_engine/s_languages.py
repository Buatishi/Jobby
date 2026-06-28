from typing import Any

from app.services.match_engine.common import clamp, normalize_text

LANGUAGE_LEVEL = {
    "basic": 1,
    "beginner": 1,
    "intermediate": 2,
    "professional": 3,
    "advanced": 3,
    "native": 4,
    "bilingual": 4,
}


def _required_languages(job: dict[str, Any]) -> list[dict[str, Any]]:
    required = job.get("required_languages")
    if isinstance(required, list):
        return [
            {"name": str(item), "level": "intermediate"}
            if not isinstance(item, dict)
            else item
            for item in required
        ]
    if isinstance(required, dict):
        values = required.get("languages", required.get("required"))
        if isinstance(values, list):
            return [
                {"name": str(item), "level": "intermediate"}
                if not isinstance(item, dict)
                else item
                for item in values
            ]
    return []


def compute_languages_score(
    profile_languages: list[dict[str, Any]],
    job: dict[str, Any],
) -> float:
    required = _required_languages(job)
    if not required:
        return 0.85

    profile_by_name = {
        normalize_text(language.get("name")): language
        for language in profile_languages
    }
    scores: list[float] = []
    for language in required:
        name = normalize_text(language.get("name"))
        profile_language = profile_by_name.get(name)
        if profile_language is None:
            scores.append(0.0)
            continue

        user_level = LANGUAGE_LEVEL.get(
            normalize_text(
                profile_language.get("proficiency") or profile_language.get("level")
            ),
            2,
        )
        required_level = LANGUAGE_LEVEL.get(normalize_text(language.get("level")), 2)
        if user_level >= required_level:
            scores.append(1.0)
        else:
            scores.append(clamp(1.0 - (required_level - user_level) * 0.25))

    return clamp(sum(scores) / len(required))
