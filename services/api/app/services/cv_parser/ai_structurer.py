import json
import re
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import settings
from app.services.ai_gateway.prompts.untrusted import UNTRUSTED_DATA_NOTICE_EN
from app.services.cv_parser.dates import first_value, normalize_date, read_period
from app.services.cv_parser.errors import CVParsingError
from app.services.text_quality import fold

DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"

# Mismo tope que `SkillCreate.name`: una skill más larga no se podría confirmar en el
# paso 3 del asistente (la API respondería 400) y solo ensuciaría el perfil.
MAX_SKILL_NAME_LENGTH = 200
_LIST_SEPARATORS = "·•|;,\n"
_NAME_KEYS = ("name", "skill", "skill_name", "technology")
# Nombres con los que la IA suele escribir cada fecha (Decisión 41).
_START_KEYS = ("started_at", "start_date", "from")
_END_KEYS = ("ended_at", "end_date", "to", "until")
_CURRENT_KEYS = ("is_current", "current", "present", "ongoing")
_STUDY_END_KEYS = (*_END_KEYS, "graduation_date", "graduated_at", "graduation_year")
_ONGOING_KEYS = ("is_ongoing", "ongoing", "in_progress", "current")
_ISSUE_KEYS = ("issued_at", "issue_date", "issued", "date", "year", "obtained_at")
# Dónde puede venir el texto de una viñeta cuando la IA la devuelve como objeto.
_BULLET_KEYS = (
    "text",
    "description",
    "achievement",
    "bullet",
    "name",
    "title",
    "value",
)
_BULLET_DEPTH = 3
# El punto medio solo es viñeta al empezar un renglón: dentro de una línea separa
# términos («Python · SQL») y no debe partir una viñeta en dos.
_BULLET_BREAK = re.compile(r"[\r\n]+|[•●▪◦]")
_BULLET_MARKER = re.compile(r"^[\s•●▪◦·*\-–—]+")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜÑ¿¡])")


class ParsedSkill(BaseModel):
    name: str = ""
    category: str = "general"
    level: str = "unknown"


class ParsedExperience(BaseModel):
    company: str = ""
    title: str = ""
    # Las fechas son `AAAA-MM`/`AAAA` o, si el CV no es claro, como las escribió el CV.
    started_at: str | None = None
    ended_at: str | None = None
    is_current: bool = False
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)


class ParsedEducation(BaseModel):
    institution: str = ""
    field_of_study: str | None = None
    degree_level: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    is_ongoing: bool = False


class ParsedLanguage(BaseModel):
    name: str = ""
    level: str = "unknown"


class ParsedCertification(BaseModel):
    name: str = ""
    issuer: str | None = None
    issued_at: str | None = None


class ParsedContact(BaseModel):
    # Encabezado del CV descargable: solo lo que figura en el CV, nunca inventado.
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""


class CVStructuredData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contact: ParsedContact = Field(default_factory=ParsedContact)
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
        "with this shape: contact, skills, experiences, educations, languages, "
        "certifications. Do not include markdown, comments, or extra keys. "
        "Each skill, experience, education, language and certification is an "
        "object: skills {name, category, level}; experiences {company, title, "
        "started_at, ended_at, is_current, description, achievements}; educations "
        "{institution, field_of_study, degree_level, started_at, ended_at, "
        "is_ongoing}; languages {name, level}; certifications {name, issuer, "
        "issued_at}. List every skill, technology and tool the CV mentions as "
        "its own skills object, including those written in a single line. "
        "Use lowercase categories and levels when possible. "
        'Copy each date exactly as the CV writes it ("Julio 2026", "03/2021", '
        '"2019"); leave it empty when the CV gives none. If a job or a study '
        'continues ("Presente", "Actual", "Actualidad", "Present", "En curso"), '
        "put that word in ended_at and set is_current or is_ongoing to true. "
        "Put each bullet of a job as its own string in achievements; description "
        "is only the text that is not a bullet and must never repeat them. "
        f"{UNTRUSTED_DATA_NOTICE_EN}"
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
        "Rules: return only one JSON object. contact must be an object with "
        "full_name, email, phone, location and linkedin_url, copied exactly as "
        "they appear in the CV. Every other top-level key must be an array. "
        "Use empty strings for unknown text values, never null. "
        "achievements must always be an array of strings. "
        "is_current and is_ongoing must be true or false.\n\n"
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


def _bullet_key(text: str) -> str:
    """Las palabras de un texto sin acentos, mayúsculas ni signos, para compararlo."""
    return " ".join(re.findall(r"[^\W_]+", fold(text)))


def _bullets(value: Any, depth: int = 0) -> list[str]:
    """Una viñeta por elemento, venga como lista, como objetos o como un texto.

    La IA devuelve a veces las viñetas de una experiencia en un solo texto con
    renglones («• A\\n• B») o como objetos; solo cuenta el texto. Un número o un
    booleano no es una viñeta.
    """
    if depth > _BULLET_DEPTH:
        return []
    if isinstance(value, str):
        pieces = (
            _BULLET_MARKER.sub("", piece).strip()
            for piece in _BULLET_BREAK.split(value)
        )
        return [piece for piece in pieces if piece]
    if isinstance(value, dict):
        for key in _BULLET_KEYS:
            bullets = _bullets(value.get(key), depth + 1)
            if bullets:
                return bullets
        return []
    if isinstance(value, list):
        return [bullet for item in value for bullet in _bullets(item, depth + 1)]
    return []


def _unique_bullets(value: Any) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for bullet in _bullets(value):
        key = _bullet_key(bullet)
        if key and key not in seen:
            seen.add(key)
            unique.append(bullet)
    return unique


def _without_bullets(description: str, bullets: list[str]) -> str:
    """La descripción sin las oraciones que ya están como viñetas.

    La web muestra la descripción en viñetas y después los logros: si la IA repite los
    mismos en los dos campos, el CV descargable los imprime dos veces. Solo sale una
    oración que coincide entera; una que comparte una parte con una viñeta se conserva.
    """
    if not description or not bullets:
        return description
    covered = {_bullet_key(bullet) for bullet in bullets}
    for bullet in bullets:
        covered.update(_bullet_key(part) for part in _SENTENCE_BREAK.split(bullet))
    covered.discard("")

    segments = [
        sentence.strip()
        for line in _BULLET_BREAK.split(description)
        for sentence in _SENTENCE_BREAK.split(_BULLET_MARKER.sub("", line).strip())
        if sentence.strip()
    ]
    kept = [segment for segment in segments if _bullet_key(segment) not in covered]
    if len(kept) == len(segments):
        return description
    return " ".join(kept)


def _normalize_items(value: Any) -> list[dict[str, Any]]:
    return [item for item in _ensure_list(value) if isinstance(item, dict)]


def _split_list_text(text: str) -> list[str]:
    """Separa «Python · React, SQL» sin partir lo que está entre paréntesis."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char in "([":
            depth += 1
        elif char in ")]":
            depth = max(0, depth - 1)
        if depth == 0 and char in _LIST_SEPARATORS:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    cleaned = (part.strip(" \t-–—") for part in parts)
    return [part for part in cleaned if part]


def _skill_entries(raw: Any, category: str = "general") -> list[dict[str, str]]:
    """Las skills del CV, con la forma que la IA las haya devuelto.

    El prompt no fijaba la forma de cada ítem y la IA devuelve a veces objetos, a veces
    strings sueltos, un solo texto separado por «·» o un objeto agrupado por categoría.
    Solo se aceptaban objetos: con una lista de strings el CV quedaba sin skills, sin
    ningún error.
    """
    entries: list[dict[str, str]] = []
    if isinstance(raw, str):
        for name in _split_list_text(raw):
            entries.append({"name": name, "category": category, "level": "unknown"})
    elif isinstance(raw, dict):
        if any(key in raw for key in _NAME_KEYS):
            entries.extend(_skill_entries([raw], category))
        else:
            for group, value in raw.items():
                if isinstance(value, list | str):
                    entries.extend(_skill_entries(value, _clean_str(group) or category))
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                name = _pick(item, *_NAME_KEYS)
                if name:
                    entries.append(
                        {
                            "name": name,
                            "category": _pick(
                                item, "category", "type", default=category
                            ),
                            "level": _pick(
                                item, "level", "proficiency", default="unknown"
                            ),
                        }
                    )
            elif isinstance(item, str):
                entries.extend(_skill_entries(item, category))
    return entries


def _normalize_structured_payload(parsed: dict[str, Any]) -> dict[str, Any]:
    for wrapper_key in ("data", "profile", "parsed_data", "cv"):
        wrapped = parsed.get(wrapper_key)
        if isinstance(wrapped, dict):
            parsed = wrapped
            break

    raw_contact = parsed.get("contact")
    contact_item = raw_contact if isinstance(raw_contact, dict) else {}
    contact = {
        "full_name": _pick(contact_item, "full_name", "name"),
        "email": _pick(contact_item, "email", "mail"),
        "phone": _pick(contact_item, "phone", "telephone", "mobile"),
        "location": _pick(contact_item, "location", "city", "address"),
        "linkedin_url": _pick(contact_item, "linkedin_url", "linkedin"),
    }

    skills: list[dict[str, str]] = []
    seen_skills: set[str] = set()
    for entry in _skill_entries(parsed.get("skills")):
        # La misma skill repetida (otra categoría o mayúscula) cuenta una sola vez.
        key = entry["name"].lower()
        if len(entry["name"]) > MAX_SKILL_NAME_LENGTH or key in seen_skills:
            continue
        seen_skills.add(key)
        skills.append(entry)

    experiences = []
    for item in _normalize_items(parsed.get("experiences")):
        title = _pick(item, "title", "role", "position", "job_title")
        company = _pick(item, "company", "employer", "organization")
        if not title and not company:
            continue
        achievements = _unique_bullets(item.get("achievements"))
        started_at, ended_at, is_current = read_period(
            item, _START_KEYS, _END_KEYS, _CURRENT_KEYS
        )
        experiences.append(
            {
                "company": company,
                "title": title,
                "started_at": started_at,
                "ended_at": ended_at,
                "is_current": is_current,
                "description": _without_bullets(
                    _pick(item, "description", "summary"), achievements
                ),
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
        started_at, ended_at, is_ongoing = read_period(
            item, _START_KEYS, _STUDY_END_KEYS, _ONGOING_KEYS
        )
        educations.append(
            {
                "institution": institution,
                "field_of_study": field,
                "degree_level": degree,
                "started_at": started_at,
                "ended_at": ended_at,
                "is_ongoing": is_ongoing,
            }
        )

    languages = []
    for item in _ensure_list(parsed.get("languages")):
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict):
            continue
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
    for item in _ensure_list(parsed.get("certifications")):
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict):
            continue
        name = _pick(item, "name", "certification", "title")
        if not name:
            continue
        certifications.append(
            {
                "name": name,
                "issuer": _pick(item, "issuer", "organization", "authority"),
                "issued_at": normalize_date(first_value(item, _ISSUE_KEYS)),
            }
        )

    return {
        "contact": contact,
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
