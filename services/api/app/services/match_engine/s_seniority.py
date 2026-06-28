from typing import Any

from app.services.match_engine.common import clamp, normalize_text

SENIORITY_ORDER = {
    "junior": 1,
    "mid": 2,
    "middle": 2,
    "senior": 3,
    "staff": 4,
    "principal": 5,
}


def compute_seniority_score(profile: dict[str, Any], job: dict[str, Any]) -> float:
    user_level = SENIORITY_ORDER.get(normalize_text(profile.get("target_seniority")))
    required_level = SENIORITY_ORDER.get(normalize_text(job.get("required_seniority")))
    if not user_level or not required_level:
        return 0.75

    delta = user_level - required_level
    if delta >= 0:
        return 1.0 if delta <= 1 else 0.9

    penalty_by_gap = {1: 0.75, 2: 0.45, 3: 0.25, 4: 0.10}
    return clamp(penalty_by_gap.get(abs(delta), 0.10))
