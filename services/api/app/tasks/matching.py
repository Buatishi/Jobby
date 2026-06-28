import asyncio
from typing import Any

from app.database import get_supabase_client
from app.services.match_engine import MatchEngine
from app.tasks import celery_app


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


async def _fetch_skill_names(supabase: Any, profile_id: str) -> list[str]:
    data = await _execute(
        supabase.table("skills")
        .select("name")
        .eq("profile_id", profile_id)
        .eq("confirmed", True)
    )
    if isinstance(data, list):
        return [
            str(row["name"])
            for row in data
            if isinstance(row, dict) and row.get("name")
        ]
    return []


async def _fetch_job(supabase: Any, job_id: str) -> dict[str, Any]:
    data = await _execute(
        supabase.table("job_descriptions").select("*").eq("id", job_id).single()
    )
    if not isinstance(data, dict):
        raise ValueError(f"Job {job_id} not found.")
    return data


def _required_skill_names(job: dict[str, Any]) -> list[str]:
    required_skills = job.get("required_skills")
    if isinstance(required_skills, list):
        return [str(skill) for skill in required_skills]
    if isinstance(required_skills, dict):
        values = required_skills.get("skills")
        if isinstance(values, list):
            return [str(skill) for skill in values]
    return []


async def run_match(
    job_id: str,
    profile_id: str,
    supabase: Any | None = None,
) -> dict[str, Any]:
    supabase_client = supabase or await get_supabase_client()
    job = await _fetch_job(supabase_client, job_id)
    candidate_skills = await _fetch_skill_names(supabase_client, profile_id)
    required_skills = _required_skill_names(job)
    score = await MatchEngine().score(candidate_skills, required_skills)
    match_score = round(score * 100)
    matched_skills = sorted(set(candidate_skills).intersection(required_skills))

    payload = {
        "user_id": job["user_id"],
        "profile_id": profile_id,
        "job_id": job_id,
        "match_score": match_score,
        "potential_score": match_score,
        "representation_score": match_score,
        "gap_origin": "skills" if match_score < 100 else "none",
        "score_breakdown": {
            "matched_skills": matched_skills,
            "required_skills": required_skills,
        },
        "recommendations": [],
        "ai_model_used": "rule-based-v0",
    }
    data = await _execute(supabase_client.table("job_matches").insert(payload))
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    if isinstance(data, dict):
        return data
    return payload


@celery_app.task(name="app.tasks.matching.match_task", queue="analysis")  # type: ignore[untyped-decorator]
def match_task(job_id: str, profile_id: str) -> dict[str, Any]:
    return asyncio.run(run_match(job_id, profile_id))


def enqueue_match(job_id: str, profile_id: str) -> str:
    async_result = match_task.delay(job_id, profile_id)
    return str(async_result.id)
