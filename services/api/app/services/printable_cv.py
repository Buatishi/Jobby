"""Arma los datos del CV descargable (Decisión 26).

El contenido sale del perfil que la persona confirmó; si una sección está vacía (por
ejemplo, si salteó el último paso del asistente), se usa lo que leyó el CV principal.
El encabezado sale del CV principal y, si falta, de la cuenta y del perfil.
"""

from typing import Any

from app.models.profiles import (
    PrintableCV,
    PrintableCVCertification,
    PrintableCVContact,
    PrintableCVEducation,
    PrintableCVExperience,
    PrintableCVLanguage,
)


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _level(value: Any) -> str | None:
    # El lector de CV marca «unknown» cuando el nivel no figura: no se imprime.
    level = _text(value)
    return level if level and level.lower() != "unknown" else None


def _rows_or_parsed(
    rows: list[dict[str, Any]],
    parsed_data: dict[str, Any],
    key: str,
) -> list[dict[str, Any]]:
    if rows:
        return rows
    parsed = parsed_data.get(key)
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _contact(
    parsed_data: dict[str, Any],
    profile: dict[str, Any],
    account_email: str,
) -> PrintableCVContact:
    raw = parsed_data.get("contact")
    parsed = raw if isinstance(raw, dict) else {}
    return PrintableCVContact(
        full_name=_text(parsed.get("full_name")),
        email=_text(parsed.get("email")) or account_email,
        phone=_text(parsed.get("phone")),
        location=_text(parsed.get("location")),
        linkedin_url=(
            _text(parsed.get("linkedin_url")) or _text(profile.get("linkedin_url"))
        ),
    )


def build_printable_cv(
    *,
    profile: dict[str, Any],
    primary_cv: dict[str, Any] | None,
    account_email: str,
    skills: list[dict[str, Any]],
    experiences: list[dict[str, Any]],
    educations: list[dict[str, Any]],
    languages: list[dict[str, Any]],
    certifications: list[dict[str, Any]],
) -> PrintableCV:
    raw_parsed = (primary_cv or {}).get("parsed_data")
    parsed_data = raw_parsed if isinstance(raw_parsed, dict) else {}

    skill_names: list[str] = []
    for item in _rows_or_parsed(skills, parsed_data, "skills"):
        name = _text(item.get("name"))
        if name and name.lower() not in {existing.lower() for existing in skill_names}:
            skill_names.append(name)

    experience_items = [
        PrintableCVExperience(
            company=_text(item.get("company")),
            title=_text(item.get("title")),
            started_at=_text(item.get("started_at")) or None,
            ended_at=_text(item.get("ended_at")) or None,
            is_current=bool(item.get("is_current")),
            description=_text(item.get("description")) or None,
            achievements=[
                _text(achievement)
                for achievement in item.get("achievements") or []
                if _text(achievement)
            ],
        )
        for item in _rows_or_parsed(experiences, parsed_data, "experiences")
    ]
    # Lo más reciente primero, como se lee un CV; sin fecha, al final.
    experience_items.sort(key=lambda item: item.started_at or "", reverse=True)

    return PrintableCV(
        contact=_contact(parsed_data, profile, account_email),
        headline=_text(profile.get("headline")) or None,
        summary=_text(profile.get("summary")) or None,
        skills=skill_names,
        experiences=experience_items,
        educations=[
            PrintableCVEducation(
                institution=_text(item.get("institution")),
                field_of_study=_text(item.get("field_of_study")) or None,
                degree_level=_text(item.get("degree_level")) or None,
            )
            for item in _rows_or_parsed(educations, parsed_data, "educations")
        ],
        languages=[
            PrintableCVLanguage(
                name=_text(item.get("name")),
                level=_level(item.get("proficiency") or item.get("level")),
            )
            for item in _rows_or_parsed(languages, parsed_data, "languages")
            if _text(item.get("name"))
        ],
        certifications=[
            PrintableCVCertification(
                name=_text(item.get("name")),
                issuer=_text(item.get("issuer")) or None,
            )
            for item in _rows_or_parsed(certifications, parsed_data, "certifications")
            if _text(item.get("name"))
        ],
    )
