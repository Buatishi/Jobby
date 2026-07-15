import json
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import settings
from app.services.cv_parser.errors import CVParsingError

DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"


class ParsedSkill(BaseModel):
    name: str = ""
    category: str = "general"
    level: str = "unknown"


class ParsedExperience(BaseModel):
    company: str = ""
    title: str = ""
    started_at: str | None = None
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)


class ParsedEducation(BaseModel):
    institution: str = ""
    field_of_study: str | None = None
    degree_level: str | None = None


class ParsedLanguage(BaseModel):
    name: str = ""
    level: str = "unknown"


class ParsedCertification(BaseModel):
    name: str = ""
    issuer: str | None = None


class CVStructuredData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    skills: list[ParsedSkill] = Field(default_factory=list)
    experiences: list[ParsedExperience] = Field(default_factory=list)
    educations: list[ParsedEducation] = Field(default_factory=list)
    languages: list[ParsedLanguage] = Field(default_factory=list)
    certifications: list[ParsedCertification] = Field(default_factory=list)


def _deepseek_api_key() -> str:
    return settings.deepseek_api_key.strip().strip('"').strip("'")


def _system_prompt() -> str:
    return (
        "You are a bilingual CV parser for Spanish and English resumes. "
        "Extract only facts explicitly present in the CV. Return strict JSON "
        "with this shape: skills, experiences, educations, languages, "
        "certifications. Do not include markdown, comments, or extra keys. "
        "Use lowercase categories and levels when possible."
    )


def _user_prompt(cv_text: str, correction_hint: str | None = None) -> str:
    correction = ""
    if correction_hint:
        correction = (
            "\nYour previous response failed validation. Correct it. "
            f"Validation error: {correction_hint}\n"
        )

    return (
        f"{correction}\nExtract structured data from this CV/resume text. "
        "The CV may be in Spanish, English, or both.\n\n"
        "Rules: return only one JSON object. Each top-level key must be an "
        "array. Use empty strings for unknown text values, never null. "
        "achievements must always be an array of strings.\n\n"
        f"{cv_text}"
    )


def _clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _pick(item: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return _clean_str(item[key], default)
    return default


def _normalize_items(value: Any) -> list[dict[str, Any]]:
    return [item for item in _ensure_list(value) if isinstance(item, dict)]


def _normalize_structured_payload(parsed: dict[str, Any]) -> dict[str, Any]:
    for wrapper_key in ("data", "profile", "parsed_data", "cv"):
        wrapped = parsed.get(wrapper_key)
        if isinstance(wrapped, dict):
            parsed = wrapped
            break

    skills = []
    for item in _normalize_items(parsed.get("skills")):
        name = _pick(item, "name", "skill", "skill_name", "technology")
        if not name:
            continue
        skills.append(
            {
                "name": name,
                "category": _pick(item, "category", "type", default="general"),
                "level": _pick(item, "level", "proficiency", default="unknown"),
            }
        )

    experiences = []
    for item in _normalize_items(parsed.get("experiences")):
        title = _pick(item, "title", "role", "position", "job_title")
        company = _pick(item, "company", "employer", "organization")
        if not title and not company:
            continue
        achievements = [
            _clean_str(achievement)
            for achievement in _ensure_list(item.get("achievements"))
            if _clean_str(achievement)
        ]
        experiences.append(
            {
                "company": company,
                "title": title,
                "started_at": _pick(item, "started_at", "start_date", "from"),
                "description": _pick(item, "description", "summary"),
                "achievements": achievements,
            }
        )

    educations = []
    for item in _normalize_items(parsed.get("educations")):
        institution = _pick(item, "institution", "school", "university")
        field = _pick(item, "field_of_study", "field", "area")
        degree = _pick(item, "degree_level", "degree", "title")
        if not institution and not field and not degree:
            continue
        educations.append(
            {
                "institution": institution,
                "field_of_study": field,
                "degree_level": degree,
            }
        )

    languages = []
    for item in _normalize_items(parsed.get("languages")):
        name = _pick(item, "name", "language")
        if not name:
            continue
        languages.append(
            {
                "name": name,
                "level": _pick(item, "level", "proficiency", default="unknown"),
            }
        )

    certifications = []
    for item in _normalize_items(parsed.get("certifications")):
        name = _pick(item, "name", "certification", "title")
        if not name:
            continue
        certifications.append(
            {
                "name": name,
                "issuer": _pick(item, "issuer", "organization", "authority"),
            }
        )

    return {
        "skills": skills,
        "experiences": experiences,
        "educations": educations,
        "languages": languages,
        "certifications": certifications,
    }


def _extract_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise CVParsingError("DeepSeek no devolvió contenido.", "AI_EMPTY_RESPONSE")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise CVParsingError("Respuesta AI inválida.", "AI_INVALID_RESPONSE")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise CVParsingError("DeepSeek devolvió contenido vacío.", "AI_EMPTY_RESPONSE")

    return content


def _parse_json_content(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise CVParsingError(
            "DeepSeek no devolvió JSON válido.",
            "AI_INVALID_JSON",
        ) from exc

    if not isinstance(parsed, dict):
        raise CVParsingError(
            "El JSON estructurado debe ser un objeto.",
            "AI_INVALID_JSON",
        )

    return parsed


async def _call_deepseek(cv_text: str, correction_hint: str | None = None) -> str:
    api_key = _deepseek_api_key()
    if not api_key:
        raise CVParsingError("Falta DEEPSEEK_API_KEY.", "DEEPSEEK_NOT_CONFIGURED")

    payload = {
        "model": "deepseek-chat",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": _user_prompt(cv_text, correction_hint)},
        ],
        "temperature": 0.1,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(DEEPSEEK_CHAT_URL, json=payload, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code == 401:
                raise CVParsingError(
                    "DeepSeek rechazo la API key configurada. "
                    "Revisa DEEPSEEK_API_KEY en Render.",
                    "DEEPSEEK_UNAUTHORIZED",
                ) from exc
            raise CVParsingError(
                f"DeepSeek devolvio HTTP {status_code}.",
                "DEEPSEEK_REQUEST_FAILED",
            ) from exc
        response_payload = response.json()

    return _extract_content(response_payload)


async def structure_cv_text(cv_text: str) -> CVStructuredData:
    validation_error: str | None = None

    for _attempt in range(2):
        content = await _call_deepseek(cv_text, validation_error)
        parsed_json = _parse_json_content(content)
        normalized_json = _normalize_structured_payload(parsed_json)
        try:
            return CVStructuredData.model_validate(normalized_json)
        except ValidationError as exc:
            validation_error = str(exc)

    raise CVParsingError(
        "No se pudo validar el JSON estructurado del CV.",
        "AI_VALIDATION_FAILED",
    )
