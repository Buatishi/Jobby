import math
from typing import Any


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


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


def count_semantic_matches(
    profile_items: list[dict[str, Any]],
    job_items: list[dict[str, Any]],
    threshold: float = 0.82,
) -> int:
    matched_profile_indexes: set[int] = set()
    count = 0

    for job_item in job_items:
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
            count += 1

    return count
