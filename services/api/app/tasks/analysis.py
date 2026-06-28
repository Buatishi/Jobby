import asyncio
import json
import re
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import ValidationError

from app.database import get_supabase_client
from app.models.interview_kits import InterviewKitContent
from app.models.jobs import StructuredJobDescription
from app.services.ai_gateway import AIGateway, PremiumRequiredError
from app.services.ai_gateway.prompts.interview_kit_v1 import (
    SYSTEM_PROMPT as INTERVIEW_KIT_SYSTEM_PROMPT,
)
from app.services.ai_gateway.prompts.interview_kit_v1 import build_user_prompt
from app.services.match_engine import MatchResult, compute_match_score
from app.services.scraper import linkedin_scraper, scrape_url
from app.tasks import celery_app

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


async def _fetch_user_tier(supabase: Any, user_id: str) -> Literal["free", "premium"]:
    data = await _execute(
        supabase.table("users").select("tier").eq("id", user_id).single()
    )
    if isinstance(data, dict) and data.get("tier") == "premium":
        return "premium"
    return "free"


async def _fetch_job(supabase: Any, job_id: str) -> dict[str, Any]:
    data = await _execute(
        supabase.table("job_descriptions").select("*").eq("id", job_id).single()
    )
    if not isinstance(data, dict):
        raise ValueError(f"Job {job_id} not found.")
    return data


async def _fetch_profile(supabase: Any, profile_id: str) -> dict[str, Any]:
    data = await _execute(
        supabase.table("master_profiles").select("*").eq("id", profile_id).single()
    )
    if not isinstance(data, dict):
        raise ValueError(f"Profile {profile_id} not found.")
    return data


async def _fetch_interview_kit(supabase: Any, kit_id: str) -> dict[str, Any]:
    data = await _execute(
        supabase.table("interview_kits").select("*").eq("id", kit_id).single()
    )
    if not isinstance(data, dict):
        raise ValueError(f"Interview kit {kit_id} not found.")
    return data


async def _fetch_profile_rows(
    supabase: Any,
    table_name: str,
    profile_id: str,
) -> list[dict[str, Any]]:
    data = await _execute(
        supabase.table(table_name).select("*").eq("profile_id", profile_id)
    )
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


async def _fetch_primary_cv(supabase: Any, user_id: str) -> dict[str, Any] | None:
    data = await _execute(
        supabase.table("uploaded_documents")
        .select("*")
        .eq("user_id", user_id)
        .eq("type", "cv")
        .eq("is_primary", True)
        .single()
    )
    return data if isinstance(data, dict) else None


async def _assert_interview_kit_limit(supabase: Any, user_id: str) -> None:
    data = await _execute(
        supabase.table("interview_kits").select("*").eq("user_id", user_id)
    )
    rows = (
        [row for row in data if isinstance(row, dict)]
        if isinstance(data, list)
        else []
    )
    now = datetime.now(UTC)
    current_month_count = 0
    for row in rows:
        created_at = str(row.get("created_at") or "")
        if created_at.startswith(f"{now.year:04d}-{now.month:02d}"):
            current_month_count += 1
    if current_month_count >= 10:
        raise ValueError("Interview Kits mensuales agotados.")


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


def _cv_text(primary_cv: dict[str, Any] | None) -> str:
    if not primary_cv or not isinstance(primary_cv.get("parsed_data"), dict):
        return "No disponible"
    parsed_data = primary_cv["parsed_data"]
    chunks: list[str] = []
    for key in ("skills", "experiences", "educations", "languages", "certifications"):
        chunks.append(f"{key}: {parsed_data.get(key, [])}")
    return "\n".join(chunks)


def _parse_interview_kit(content: str) -> InterviewKitContent:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Claude returned invalid interview kit JSON.") from exc
    try:
        return InterviewKitContent.model_validate(parsed)
    except ValidationError as exc:
        raise ValueError("Interview kit JSON failed validation.") from exc


def _reasoning_prompt(job: dict[str, Any], result: MatchResult) -> str:
    return (
        "Explicá en bullets concretos por qué este candidato tiene un match "
        f"score de {result.match_score} para este puesto.\n"
        "Listá 3-5 recomendaciones accionables específicas "
        "(ej: 'Agregá React al CV', 'Mencioná liderazgo').\n\n"
        f"Puesto: {job.get('job_title')}\n"
        f"Empresa: {job.get('company_name')}\n"
        f"Score breakdown: {json.dumps(result.score_breakdown, ensure_ascii=False)}"
    )


def _recommendations_from_reasoning(reasoning: str) -> list[dict[str, str]]:
    lines = [
        re.sub(r"^[-*•\d.\s]+", "", line).strip()
        for line in reasoning.splitlines()
    ]
    concrete_lines = [line for line in lines if line]
    recommendations = concrete_lines[-5:] if len(concrete_lines) > 5 else concrete_lines
    return [
        {
            "title": item[:80],
            "description": item,
            "priority": "high" if index == 0 else "medium",
        }
        for index, item in enumerate(recommendations[:5])
    ]


async def run_match(
    job_id: str,
    profile_id: str,
    user_id: str,
    supabase: Any | None = None,
    gateway: AIGateway | None = None,
) -> dict[str, Any]:
    supabase_client = supabase or await get_supabase_client()
    ai_gateway = gateway or AIGateway()
    job = await _fetch_job(supabase_client, job_id)
    user_tier = await _fetch_user_tier(supabase_client, user_id)
    result = await compute_match_score(profile_id, job_id, supabase_client)
    reasoning = await ai_gateway.generate(
        "match_reasoning",
        user_tier,
        _reasoning_prompt(job, result),
        system=(
            "Sos un coach laboral bilingüe. Respondé en español, con bullets "
            "concretos y recomendaciones específicas. No uses markdown complejo."
        ),
    )
    recommendations = _recommendations_from_reasoning(reasoning)

    payload: dict[str, Any] = {
        "user_id": user_id,
        "profile_id": profile_id,
        "job_id": job_id,
        "match_score": result.match_score,
        "potential_score": result.potential_score,
        "representation_score": result.representation_score,
        "gap_origin": result.gap_origin,
        "score_breakdown": {
            **result.score_breakdown,
            "reasoning": reasoning,
        },
        "recommendations": recommendations,
        "ai_model_used": "claude-sonnet-4-5"
        if user_tier == "premium"
        else "deepseek-chat",
    }
    data = await _execute(supabase_client.table("job_matches").insert(payload))
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    if isinstance(data, dict):
        return data
    return payload


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
    enqueue_match(job_id, profile_id, user_id)

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


@celery_app.task(name="app.tasks.analysis.match_task", queue="analysis")  # type: ignore[untyped-decorator]
def match_task(job_id: str, profile_id: str, user_id: str) -> dict[str, Any]:
    return asyncio.run(run_match(job_id, profile_id, user_id))


def enqueue_match(job_id: str, profile_id: str, user_id: str) -> str:
    async_result = match_task.delay(job_id, profile_id, user_id)
    return str(async_result.id)


async def run_interview_kit(
    kit_id: str,
    user_id: str,
    supabase: Any | None = None,
    gateway: AIGateway | None = None,
) -> dict[str, Any]:
    supabase_client = supabase or await get_supabase_client()
    ai_gateway = gateway or AIGateway()
    user_tier = await _fetch_user_tier(supabase_client, user_id)
    if user_tier != "premium":
        raise PremiumRequiredError("interview_kit")

    await _assert_interview_kit_limit(supabase_client, user_id)
    kit = await _fetch_interview_kit(supabase_client, kit_id)
    await _execute(
        supabase_client.table("interview_kits")
        .update({"status": "processing", "error_msg": None})
        .eq("id", kit_id)
    )

    try:
        profile = await _fetch_profile(supabase_client, str(kit["profile_id"]))
        job = await _fetch_job(supabase_client, str(kit["job_id"]))
        skills = await _fetch_profile_rows(
            supabase_client,
            "skills",
            str(kit["profile_id"]),
        )
        experiences = await _fetch_profile_rows(
            supabase_client,
            "experiences",
            str(kit["profile_id"]),
        )
        primary_cv = await _fetch_primary_cv(supabase_client, user_id)
        raw_metadata = kit.get("prep_notes")
        metadata: dict[str, Any] = (
            raw_metadata if isinstance(raw_metadata, dict) else {}
        )
        company_url = (
            metadata.get("company_linkedin_url")
            or job.get("source_url")
            or ""
        )
        interviewer_url = metadata.get("interviewer_linkedin_url") or ""

        company_data: dict[str, Any] | str = "No disponible"
        if company_url:
            company_data = await linkedin_scraper.scrape_company(
                str(company_url),
                db=supabase_client,
                user_id=user_id,
            )
        person_data: dict[str, Any] = {}
        if interviewer_url:
            person_data = await linkedin_scraper.scrape_person(
                str(interviewer_url),
                db=supabase_client,
                user_id=user_id,
                candidate_context={
                    "skills": [
                        skill.get("name")
                        for skill in skills
                        if skill.get("name")
                    ]
                },
            )

        prompt = build_user_prompt(
            nombre=str(profile.get("headline") or profile.get("id")),
            cv_text=_cv_text(primary_cv),
            skills=skills,
            experiences=experiences,
            company_name=str(job.get("company_name") or "No disponible"),
            job_title=str(job.get("job_title") or "No disponible"),
            job_description=str(job.get("raw_text") or job.get("job_title") or ""),
            company_data_or_no_disponible=company_data,
            interviewer_name=str(
                metadata.get("interviewer_name")
                or person_data.get("full_name")
                or "No disponible"
            ),
            interviewer_role=str(
                metadata.get("interviewer_role")
                or person_data.get("current_role")
                or "No disponible"
            ),
            role_type=str(person_data.get("role_type") or "Hiring Manager"),
            background_summary=str(person_data.get("background_summary") or ""),
        )
        content = await ai_gateway.generate(
            "interview_kit",
            "premium",
            prompt,
            system=INTERVIEW_KIT_SYSTEM_PROMPT,
            json_mode=True,
        )
        kit_content = _parse_interview_kit(content)
        payload: dict[str, Any] = {
            "title": f"Interview Kit - {job.get('job_title') or 'Puesto'}",
            "questions": {
                "model_answers": [
                    answer.model_dump() for answer in kit_content.model_answers
                ],
                "candidate_questions": kit_content.candidate_questions,
            },
            "prep_notes": {
                **metadata,
                **kit_content.model_dump(),
                "company_data": company_data,
                "interviewer_data": person_data,
            },
            "status": "done",
            "error_msg": None,
            "ai_model_used": "claude-sonnet-4-5",
        }
        data = await _execute(
            supabase_client.table("interview_kits").update(payload).eq("id", kit_id)
        )
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
        if isinstance(data, dict):
            return data
        return {**kit, **payload}
    except Exception as exc:
        await _execute(
            supabase_client.table("interview_kits")
            .update({"status": "failed", "error_msg": str(exc)})
            .eq("id", kit_id)
        )
        raise


@celery_app.task(name="app.tasks.analysis.interview_kit_task", queue="analysis")  # type: ignore[untyped-decorator]
def interview_kit_task(kit_id: str, user_id: str) -> dict[str, Any]:
    return asyncio.run(run_interview_kit(kit_id, user_id))


def enqueue_interview_kit(kit_id: str, user_id: str) -> str:
    async_result = interview_kit_task.delay(kit_id, user_id)
    return str(async_result.id)
