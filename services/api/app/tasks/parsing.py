import asyncio
import tempfile
from pathlib import Path
from typing import Any

from app.config import settings
from app.database import get_supabase_client
from app.services.ai_gateway import AIGateway
from app.services.cv_parser import (
    extract_pdf_text,
    merge_parsed_skills,
    structure_cv_text,
)
from app.tasks import celery_app
from app.tasks.local_fallback import enqueue_local_task

DOCUMENTS_BUCKET = "cv-documents"


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


async def _fetch_document(supabase: Any, document_id: str) -> dict[str, Any]:
    data = await _execute(
        supabase.table("uploaded_documents")
        .select("*")
        .eq("id", document_id)
        .single()
    )
    if not isinstance(data, dict):
        raise ValueError(f"Document {document_id} not found.")
    return data


async def _fetch_profile_skills(supabase: Any, profile_id: str) -> list[dict[str, Any]]:
    data = await _execute(
        supabase.table("skills").select("*").eq("profile_id", profile_id)
    )
    if isinstance(data, list):
        return [skill for skill in data if isinstance(skill, dict)]
    return []


async def _download_storage_file(supabase: Any, storage_path: str) -> bytes:
    result = await supabase.storage.from_(DOCUMENTS_BUCKET).download(storage_path)
    if isinstance(result, bytes):
        return result
    if isinstance(result, bytearray):
        return bytes(result)
    raise ValueError("Supabase Storage returned invalid file content.")


async def _write_temp_pdf(content: bytes) -> Path:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        temp_file.write(content)
        return Path(temp_file.name)
    finally:
        temp_file.close()


async def _upsert_skill_embeddings(
    supabase: Any,
    profile_id: str,
    skills: list[dict[str, Any]],
    gateway: AIGateway,
) -> None:
    for skill in skills:
        embedding = await gateway.embed(str(skill["name"]))
        payload = {
            "profile_id": profile_id,
            "name": skill["name"],
            "category": skill.get("category"),
            "level": skill.get("level"),
            "in_cv": True,
            "confirmed": skill.get("confirmed", False),
            "embedding": embedding,
        }
        await _execute(supabase.table("skills").upsert(payload))


async def run_parse_cv(
    document_id: str,
    supabase: Any | None = None,
    gateway: AIGateway | None = None,
) -> dict[str, Any]:
    supabase_client = supabase or await get_supabase_client()
    ai_gateway = gateway or AIGateway()
    document = await _fetch_document(supabase_client, document_id)

    await _execute(
        supabase_client.table("uploaded_documents")
        .update({"status": "processing"})
        .eq("id", document_id)
    )

    temp_pdf_path: Path | None = None
    try:
        file_content = await _download_storage_file(
            supabase_client,
            str(document["storage_path"]),
        )
        temp_pdf_path = await _write_temp_pdf(file_content)
        extracted_text = await extract_pdf_text(temp_pdf_path)
        structured_data = await structure_cv_text(extracted_text)
        existing_skills = await _fetch_profile_skills(
            supabase_client,
            str(document["profile_id"]),
        )
        merged_skills = merge_parsed_skills(structured_data, existing_skills)
        await _upsert_skill_embeddings(
            supabase_client,
            str(document["profile_id"]),
            merged_skills,
            ai_gateway,
        )

        parsed_data = {
            "skills": merged_skills,
            "experiences": [
                experience.model_dump() for experience in structured_data.experiences
            ],
            "educations": [
                education.model_dump() for education in structured_data.educations
            ],
            "languages": [
                language.model_dump() for language in structured_data.languages
            ],
            "certifications": [
                certification.model_dump()
                for certification in structured_data.certifications
            ],
        }
        await _execute(
            supabase_client.table("uploaded_documents")
            .update({"status": "done", "parsed_data": parsed_data, "error_msg": None})
            .eq("id", document_id)
        )
        await supabase_client.rpc(
            "compute_completeness",
            {"p_id": document["profile_id"]},
        ).execute()
        return parsed_data
    except Exception as exc:
        await _execute(
            supabase_client.table("uploaded_documents")
            .update({"status": "failed", "error_msg": str(exc)})
            .eq("id", document_id)
        )
        raise
    finally:
        if temp_pdf_path is not None:
            temp_pdf_path.unlink(missing_ok=True)


@celery_app.task(name="app.tasks.parsing.parse_cv_task", queue="parsing")  # type: ignore[untyped-decorator]
def parse_cv_task(document_id: str) -> dict[str, Any]:
    return asyncio.run(run_parse_cv(document_id))


def enqueue_parse_cv(document_id: str) -> str:
    if settings.task_execution_mode.lower() == "local":
        return enqueue_local_task(
            lambda: run_parse_cv(document_id),
            prefix="local-parse-cv",
        )

    try:
        async_result = parse_cv_task.apply_async((document_id,), retry=False)
    except Exception:
        return enqueue_local_task(
            lambda: run_parse_cv(document_id),
            prefix="local-parse-cv",
        )

    return str(async_result.id)
