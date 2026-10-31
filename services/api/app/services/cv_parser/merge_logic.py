import unicodedata
from collections.abc import Iterable
from typing import Any

from app.services.cv_parser.ai_structurer import CVStructuredData
from app.services.skill_names import canonical_skill_key


def normalize_skill_key(name: str, category: str | None) -> tuple[str, str]:
    normalized_name = unicodedata.normalize("NFKD", name.strip().lower())
    ascii_name = "".join(
        character
        for character in normalized_name
        if not unicodedata.combining(character)
    )
    normalized_category = (category or "").strip().lower()
    return " ".join(ascii_name.split()), normalized_category


def strip_embeddings(skills: list[Any]) -> list[Any]:
    """Copia de las skills sin el vector `embedding` (1536 números por fila).

    Las filas de `skills` se leen con `select("*")` y traen el vector, que ya vive en
    esa tabla. No debe copiarse a `uploaded_documents.parsed_data` ni pegarse en un
    prompt: pesa decenas de KB por CV y se paga en tokens. Lo que no es dict pasa igual.
    """
    return [
        {key: value for key, value in skill.items() if key != "embedding"}
        if isinstance(skill, dict)
        else skill
        for skill in skills
    ]


def merge_parsed_skills(
    parsed_data: CVStructuredData,
    existing_skills: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for existing_skill in existing_skills:
        key = normalize_skill_key(
            str(existing_skill.get("name", "")),
            str(existing_skill.get("category") or ""),
        )
        merged_by_key[key] = existing_skill.copy()

    for parsed_skill in parsed_data.skills:
        key = normalize_skill_key(parsed_skill.name, parsed_skill.category)
        current_skill = merged_by_key.get(key)

        if current_skill and current_skill.get("confirmed") is True:
            continue

        merged_by_key[key] = {
            **(current_skill or {}),
            "name": parsed_skill.name,
            "category": parsed_skill.category,
            "level": parsed_skill.level,
            "in_cv": True,
            "confirmed": bool(current_skill.get("confirmed", False))
            if current_skill
            else False,
        }

    return list(merged_by_key.values())


def merge_structured_cv_data(
    parsed_data: CVStructuredData,
    existing_skills: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "contact": parsed_data.contact.model_dump(),
        "skills": merge_parsed_skills(parsed_data, existing_skills),
        "experiences": [
            experience.model_dump() for experience in parsed_data.experiences
        ],
        "educations": [education.model_dump() for education in parsed_data.educations],
        "languages": [language.model_dump() for language in parsed_data.languages],
        "certifications": [
            certification.model_dump() for certification in parsed_data.certifications
        ],
    }


def skills_named_in_linkedin(
    parsed_data: CVStructuredData,
    existing_skills: list[dict[str, Any]],
) -> list[str]:
    """Ids de las skills ya guardadas que el documento de LinkedIn nombra.

    Solo marca las que la persona ya tiene: una skill que figura únicamente en
    LinkedIn no se agrega al perfil. El motor de comparación usa todas las skills
    guardadas, confirmadas o no, y un perfil de LinkedIn suele traer aptitudes que
    nadie revisó. La categoría se ignora: la IA la infiere distinto en cada documento.

    El nombre se compara con `canonical_skill_key`: «React.js» de LinkedIn marca
    «React» y «API Integrations» marca «Integración de APIs», pero «Java» no marca
    «JavaScript».
    """
    named = _canonical_names(skill.name for skill in parsed_data.skills)
    return [
        str(skill["id"])
        for skill in existing_skills
        if skill.get("id")
        and skill.get("in_linkedin") is not True
        and canonical_skill_key(skill.get("name")) in named
    ]


def _canonical_names(names: Iterable[Any]) -> set[str]:
    named = {canonical_skill_key(name) for name in names}
    named.discard("")
    return named


def linkedin_skill_names(parsed_data: Any) -> list[str]:
    """Los nombres de skills que quedaron en el `parsed_data` de un PDF de LinkedIn.

    Lo guardado es JSON de una tarea anterior: lo que no tenga la forma esperada se
    descarta en lugar de fallar, porque un CV nuevo no puede depender de él.
    """
    if not isinstance(parsed_data, dict):
        return []
    skills = parsed_data.get("skills")
    if not isinstance(skills, list):
        return []
    return [
        skill["name"]
        for skill in skills
        if isinstance(skill, dict) and isinstance(skill.get("name"), str)
    ]


def mark_skills_in_linkedin(
    skills: list[dict[str, Any]],
    linkedin_names: Iterable[Any],
) -> list[dict[str, Any]]:
    """Las skills con `in_linkedin` en verdadero si el PDF de LinkedIn las nombró.

    El PDF de LinkedIn marca solo las skills que la persona ya tenía al subirlo. Si el
    CV se sube después, sus skills nacen sin la marca y nada las volvía a marcar: el
    resultado dependía del orden de las cargas. Acá se vuelve a aplicar con los nombres
    que el PDF dejó guardados, con la misma regla de coincidencia.
    """
    named = _canonical_names(linkedin_names)
    if not named:
        return skills
    return [
        {**skill, "in_linkedin": True}
        if skill.get("in_linkedin") is not True
        and canonical_skill_key(skill.get("name")) in named
        else skill
        for skill in skills
    ]
