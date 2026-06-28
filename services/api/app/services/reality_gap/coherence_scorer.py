from typing import Any

from app.services.match_engine.common import normalize_text


def score_reality_gap(
    confirmed_skills: list[dict[str, Any]],
    rejected_skills: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rejected_names = {
        normalize_text(skill.get("name"))
        for skill in rejected_skills
        if normalize_text(skill.get("name"))
    }
    results: list[dict[str, Any]] = []

    for skill in confirmed_skills:
        name = str(skill.get("name") or "")
        normalized_name = normalize_text(name)
        if not normalized_name:
            continue

        in_cv = bool(skill.get("in_cv"))
        in_linkedin = bool(skill.get("in_linkedin"))
        not_rejected = normalized_name not in rejected_names
        coherence_score = (
            (40 if in_cv else 0)
            + (40 if in_linkedin else 0)
            + (20 if not_rejected else 0)
        )
        results.append(
            {
                "skill_id": skill.get("id"),
                "name": name,
                "category": skill.get("category"),
                "in_cv": in_cv,
                "in_linkedin": in_linkedin,
                "rejected": not not_rejected,
                "coherence_score": coherence_score,
                "recommendation": _recommendation(
                    name,
                    in_cv,
                    in_linkedin,
                    not_rejected,
                ),
            }
        )

    return sorted(results, key=lambda item: item["coherence_score"])


def _recommendation(
    name: str,
    in_cv: bool,
    in_linkedin: bool,
    not_rejected: bool,
) -> str | None:
    if not not_rejected:
        return f"Revisá si {name} debe volver al perfil o quedar rechazada."
    if not in_cv and in_linkedin:
        return f"Agregá {name} al CV para alinear tus canales."
    if in_cv and not in_linkedin:
        return f"Agregá {name} a LinkedIn."
    if not in_cv and not in_linkedin:
        return f"Mostrá evidencia de {name} en CV y LinkedIn."
    return None
