from typing import Any

from app.services.match_engine.common import clamp, normalize_text

SOFT_SKILL_SIGNALS = {
    "leadership": ["led", "managed", "directed", "lider", "gestion", "coordin"],
    "communication": ["presented", "documented", "wrote", "present", "document"],
    "ownership": ["owned", "drove", "responsible for", "responsable", "a cargo"],
    "collaboration": ["collaborated", "partnered", "trabaj con", "en conjunto"],
    "problem_solving": ["solved", "debugged", "resolved", "resolv", "solucion"],
    "analytical": ["analyzed", "measured", "evaluated", "analic", "evalu"],
    "initiative": ["proposed", "launched", "created", "propuse", "lanc"],
    "adaptability": ["migrated", "adapted", "learned", "migr", "aprend"],
    "delivery": ["delivered", "shipped", "deployed", "entregu", "lanc"],
    "impact": ["%", "reduced", "increased", "improved", "reduje", "aument"],
}


def infer_soft_skills(experiences: list[dict[str, Any]]) -> list[str]:
    text_parts: list[str] = []
    for experience in experiences:
        achievements = experience.get("achievements") or []
        if isinstance(achievements, list):
            text_parts.extend(str(item) for item in achievements)
        text_parts.append(str(experience.get("description") or ""))

    text = " ".join(text_parts).lower()
    return sorted(
        skill
        for skill, keywords in SOFT_SKILL_SIGNALS.items()
        if any(keyword in text for keyword in keywords)
    )


def compute_soft_score(
    profile: dict[str, Any],
    experiences: list[dict[str, Any]],
    job: dict[str, Any],
) -> dict[str, Any]:
    required = {
        normalize_text(skill).replace(" ", "_")
        for skill in (job.get("soft_skills") or [])
        if normalize_text(skill)
    }
    if not required:
        return {"score": 0.75, "detected": profile.get("inferred_soft_skills") or []}

    detected = set(profile.get("inferred_soft_skills") or [])
    if not detected:
        detected = set(infer_soft_skills(experiences))

    matched = detected.intersection(required)
    base = len(matched) / len(required) if required else 0.75
    bonus = min(max(0, len(detected) - len(required)) * 0.03, 0.10)
    return {"score": clamp(base + bonus), "detected": sorted(detected)}
