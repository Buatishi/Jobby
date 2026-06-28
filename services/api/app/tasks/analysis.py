import asyncio
import json
from typing import Any, Literal

from pydantic import ValidationError

from app.database import get_supabase_client
from app.models.jobs import StructuredJobDescription
from app.services.ai_gateway import AIGateway
from app.services.scraper import scrape_url
from app.tasks import celery_app
from app.tasks.matching import enqueue_match

JobSource = Literal["url", "text"]


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


async def _fetch_profile_id(supabase: Any, user_id: str) -> str:
    data = await _execute(
        supabase.table("master_profiles")
        .select("id")
        .eq("user_id", user_id)
        .single()
    )
    if not isinstance(data, dict):
        raise ValueError(f"Profile for user {user_id} not found.")
    return str(data["id"])


def _system_prompt() -> str:
    return (
        "You extract structured job descriptions from Spanish or English job posts. "
        "Return strict JSON only. Do not include markdown or commentary."
    )


def _user_prompt(job_text: str) -> str:
    return (
        "Extract this job post into JSON with keys: job_title, company_name, "
        "required_seniority, required_modality, industry, tech_stack, "
        "required_skills, soft_skills, required_education, required_languages, "
        "salary_min, salary_max, currency.\n\n"
        f"{job_text}"
    )


def _parse_structured_job(content: str) -> StructuredJobDescription:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("DeepSeek returned invalid job JSON.") from exc
    try:
        return StructuredJobDescription.model_validate(parsed)
    except ValidationError as exc:
        raise ValueError("DeepSeek job JSON failed validation.") from exc


def _embedding_input(job: StructuredJobDescription) -> str:
    return " ".join(
        [
            job.job_title or "",
            " ".join(job.tech_stack),
            " ".join(job.required_skills),
        ]
    ).strip()


async def run_job_analysis(
    job_id: str,
    user_id: str,
    source: JobSource,
    url: str | None,
    raw_text: str | None,
    supabase: Any | None = None,
    gateway: AIGateway | None = None,
) -> dict[str, Any]:
    supabase_client = supabase or await get_supabase_client()
    ai_gateway = gateway or AIGateway()
    profile_id = await _fetch_profile_id(supabase_client, user_id)

    job_text = await scrape_url(url) if source == "url" and url else raw_text
    if not job_text:
        raise ValueError("Job text is required for analysis.")

    content = await ai_gateway.generate(
        "match_reasoning",
        "free",
        _user_prompt(job_text),
        system=_system_prompt(),
        json_mode=True,
    )
    structured_job = _parse_structured_job(content)
    embedding = await ai_gateway.embed(_embedding_input(structured_job))

    payload = {
        "id": job_id,
        "user_id": user_id,
        "source_url": url,
        "raw_text": job_text,
        "job_title": structured_job.job_title,
        "company_name": structured_job.company_name,
        "required_seniority": structured_job.required_seniority,
        "required_modality": structured_job.required_modality,
        "industry": structured_job.industry,
        "tech_stack": structured_job.tech_stack,
        "required_skills": structured_job.required_skills,
        "soft_skills": structured_job.soft_skills,
        "required_education": structured_job.required_education,
        "required_languages": structured_job.required_languages,
        "salary_min": structured_job.salary_min,
        "salary_max": structured_job.salary_max,
        "currency": structured_job.currency,
        "embedding": embedding,
    }
    data = await _execute(supabase_client.table("job_descriptions").insert(payload))
    enqueue_match(job_id, profile_id)

    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    if isinstance(data, dict):
        return data
    return payload


@celery_app.task(name="app.tasks.analysis.job_analysis_task", queue="analysis")  # type: ignore[untyped-decorator]
def job_analysis_task(
    job_id: str,
    user_id: str,
    source: JobSource,
    url: str | None = None,
    raw_text: str | None = None,
) -> dict[str, Any]:
    return asyncio.run(run_job_analysis(job_id, user_id, source, url, raw_text))


def enqueue_job_analysis(
    job_id: str,
    user_id: str,
    source: JobSource,
    url: str | None,
    raw_text: str | None,
) -> str:
    async_result = job_analysis_task.delay(job_id, user_id, source, url, raw_text)
    return str(async_result.id)
