import unicodedata
from typing import Any

from app.services.cv_parser.ai_structurer import CVStructuredData


def normalize_skill_key(name: str, category: str | None) -> tuple[str, str]:
    normalized_name = unicodedata.normalize("NFKD", name.strip().lower())
    ascii_name = "".join(
        character
        for character in normalized_name
        if not unicodedata.combining(character)
    )
    normalized_category = (category or "").strip().lower()
    return " ".join(ascii_name.split()), normalized_category


def merge_parsed_skills(
    parsed_data: CVStructuredData,
    existing_skills: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for existing_skill in existing_skills:
        key = normalize_skill_key(
            str(existing_skill.get("name", "")),
            str(existing_skill.get("category") or ""),
        )
        merged_by_key[key] = existing_skill.copy()

    for parsed_skill in parsed_data.skills:
        key = normalize_skill_key(parsed_skill.name, parsed_skill.category)
        current_skill = merged_by_key.get(key)

        if current_skill and current_skill.get("confirmed") is True:
            continue

        merged_by_key[key] = {
            **(current_skill or {}),
            "name": parsed_skill.name,
            "category": parsed_skill.category,
            "level": parsed_skill.level,
            "in_cv": True,
            "confirmed": bool(current_skill.get("confirmed", False))
            if current_skill
            else False,
        }

    return list(merged_by_key.values())


def merge_structured_cv_data(
    parsed_data: CVStructuredData,
    existing_skills: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "skills": merge_parsed_skills(parsed_data, existing_skills),
        "experiences": [
            experience.model_dump() for experience in parsed_data.experiences
        ],
        "educations": [education.model_dump() for education in parsed_data.educations],
        "languages": [language.model_dump() for language in parsed_data.languages],
        "certifications": [
            certification.model_dump() for certification in parsed_data.certifications
        ],
    }
