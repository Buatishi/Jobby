import math
from typing import Any

from app.services.skill_names import canonical_skill_key


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def skill_key(name: Any) -> str:
    """Con qué se compara el nombre de una skill: su forma común.

    «API REST» y «REST APIs» tienen la misma (`canonical_skill_key`). Si un nombre
    no deja nada con contenido (solo relleno), se compara como siempre, en
    minúsculas, para que siga coincidiendo consigo mismo.
    """
    return canonical_skill_key(name) or normalize_text(name)


def _has_text(experience: dict[str, Any]) -> bool:
    achievements = experience.get("achievements")
    return bool(str(experience.get("description") or "").strip()) or (
        isinstance(achievements, list)
        and any(str(item or "").strip() for item in achievements)
    )


def experiences_with_text(
    rows: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Las experiencias con qué leer: las del perfil, o las del CV si no dicen nada.

    El parseo del CV guarda sus experiencias en `parsed_data` y las filas de
    `experiences` las carga la persona a mano: quien subió el CV y no las completó tiene
    filas sin descripción ni logros, y el motor no veía nada de lo que el CV cuenta
    (Decisión 40). Si alguna fila tiene texto, manda el perfil, que es lo que la persona
    confirmó.
    """
    if any(_has_text(row) for row in rows):
        return rows
    primary_cv = next(
        (
            document
            for document in documents
            if document.get("type") == "cv" and document.get("is_primary")
        ),
        None,
    )
    parsed = primary_cv.get("parsed_data") if primary_cv else None
    items = parsed.get("experiences") if isinstance(parsed, dict) else None
    if not isinstance(items, list):
        return rows
    with_text = [item for item in items if isinstance(item, dict) and _has_text(item)]
    return with_text or rows


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def parse_embedding(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip().strip("[]")
        if not stripped:
            return []
        return [float(item.strip()) for item in stripped.split(",")]
    return []


def cosine_similarity(left: Any, right: Any) -> float:
    left_vector = parse_embedding(left)
    right_vector = parse_embedding(right)
    if not left_vector or not right_vector or len(left_vector) != len(right_vector):
        return 0.0

    dot = sum(a * b for a, b in zip(left_vector, right_vector, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left_vector))
    right_norm = math.sqrt(sum(b * b for b in right_vector))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return clamp(dot / (left_norm * right_norm))


def semantic_match_indexes(
    profile_items: list[dict[str, Any]],
    job_items: list[dict[str, Any]],
    threshold: float = 0.82,
) -> set[int]:
    """Posiciones de `job_items` que se parecen a algo del perfil.

    Cada skill del perfil respalda a lo sumo a una del puesto.
    """
    matched_profile_indexes: set[int] = set()
    matched_job_indexes: set[int] = set()

    for job_index, job_item in enumerate(job_items):
        best_index: int | None = None
        best_score = 0.0
        for index, profile_item in enumerate(profile_items):
            if index in matched_profile_indexes:
                continue
            score = cosine_similarity(
                profile_item.get("embedding"),
                job_item.get("embedding"),
            )
            if score > best_score:
                best_score = score
                best_index = index
        if best_index is not None and best_score >= threshold:
            matched_profile_indexes.add(best_index)
            matched_job_indexes.add(job_index)

    return matched_job_indexes


def count_semantic_matches(
    profile_items: list[dict[str, Any]],
    job_items: list[dict[str, Any]],
    threshold: float = 0.82,
) -> int:
    return len(semantic_match_indexes(profile_items, job_items, threshold))
