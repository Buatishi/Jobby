import json
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import settings
from app.services.cv_parser.errors import CVParsingError

DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"


class ParsedSkill(BaseModel):
    name: str
    category: str
    level: str


class ParsedExperience(BaseModel):
    company: str
    title: str
    started_at: str | None = None
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)


class ParsedEducation(BaseModel):
    institution: str
    field_of_study: str | None = None
    degree_level: str | None = None


class ParsedLanguage(BaseModel):
    name: str
    level: str


class ParsedCertification(BaseModel):
    name: str
    issuer: str | None = None


class CVStructuredData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    skills: list[ParsedSkill] = Field(default_factory=list)
    experiences: list[ParsedExperience] = Field(default_factory=list)
    educations: list[ParsedEducation] = Field(default_factory=list)
    languages: list[ParsedLanguage] = Field(default_factory=list)
    certifications: list[ParsedCertification] = Field(default_factory=list)


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
        f"{cv_text}"
    )


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
    if not settings.deepseek_api_key:
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
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(DEEPSEEK_CHAT_URL, json=payload, headers=headers)
        response.raise_for_status()
        response_payload = response.json()

    return _extract_content(response_payload)


async def structure_cv_text(cv_text: str) -> CVStructuredData:
    validation_error: str | None = None

    for _attempt in range(2):
        content = await _call_deepseek(cv_text, validation_error)
        parsed_json = _parse_json_content(content)
        try:
            return CVStructuredData.model_validate(parsed_json)
        except ValidationError as exc:
            validation_error = str(exc)

    raise CVParsingError(
        "No se pudo validar el JSON estructurado del CV.",
        "AI_VALIDATION_FAILED",
    )
