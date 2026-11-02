"""Qué dice cada documento (el CV o el PDF de LinkedIn) de las skills de la persona."""

import re
from dataclasses import dataclass
from typing import Any

from app.services.match_engine.common import skill_key

_READ = "done"


@dataclass(frozen=True)
class DocumentSide:
    """Un documento ya leído.

    `named` son las skills que nombró, por su forma común. Es `None` en un CV leído
    antes de que se guardara `extracted_skills`: ahí solo queda recurrir a las marcas
    de las skills guardadas. `text` es lo que cuenta el documento (experiencias,
    formación, certificaciones y resumen), en minúsculas, para encontrar una skill que
    nombra en una frase sin listarla.
    """

    named: dict[str, dict[str, Any]] | None
    text: str


def read_side(
    document: dict[str, Any] | None,
    list_key: str,
    *,
    fallback_ok: bool,
) -> DocumentSide | None:
    """El documento como se compara, o `None` si falta o todavía no se leyó."""
    if document is None or document.get("status") != _READ:
        return None
    parsed = document.get("parsed_data")
    if not isinstance(parsed, dict):
        parsed = {}
    named = _named_skills(parsed.get(list_key))
    if named is None and not fallback_ok:
        named = {}
    return DocumentSide(named=named, text=_document_text(parsed))


def pick_documents(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """El CV principal y el último PDF de LinkedIn. Las filas vienen de la más nueva."""
    cvs = [row for row in rows if row.get("type") == "cv"]
    cv = next((row for row in cvs if row.get("is_primary")), cvs[0] if cvs else None)
    linkedin = next((row for row in rows if row.get("type") == "linkedin"), None)
    return cv, linkedin


def mentions(side: DocumentSide, names: set[str]) -> bool:
    """¿El texto del documento nombra alguno de estos nombres como palabra completa?"""
    return any(_contains_whole_word(side.text, name.lower()) for name in names)


def _contains_whole_word(text: str, word: str) -> bool:
    """Misma regla que el ATS: «Git» no está en «Digital», ni «SQL» en «PostgreSQL»."""
    word = word.strip()
    if not word:
        return False
    pattern = rf"(?<![\w+#]){re.escape(word)}(?![\w+#])"
    return re.search(pattern, text) is not None


def _named_skills(items: Any) -> dict[str, dict[str, Any]] | None:
    """Las skills de una lista guardada por su forma común; `None` si no es una lista.

    Lo guardado es JSON de una tarea anterior: lo que no tenga la forma esperada se
    descarta en lugar de fallar.
    """
    if not isinstance(items, list):
        return None
    named: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, str):
            name: Any = item
            category: Any = None
        elif isinstance(item, dict):
            name, category = item.get("name"), item.get("category")
        else:
            continue
        if not isinstance(name, str):
            continue
        key = skill_key(name)
        if key and key not in named:
            named[key] = {
                "name": name.strip(),
                "category": category.strip()
                if isinstance(category, str) and category.strip()
                else None,
            }
    return named


def _document_text(parsed: dict[str, Any]) -> str:
    parts: list[str] = [_text(parsed.get("summary"))]
    for experience in _dicts(parsed.get("experiences")):
        parts.append(_text(experience.get("title")))
        parts.append(_text(experience.get("description")))
        achievements = experience.get("achievements")
        if isinstance(achievements, list):
            parts.extend(_text(item) for item in achievements)
    for education in _dicts(parsed.get("educations")):
        parts.append(_text(education.get("field_of_study")))
        parts.append(_text(education.get("degree_level")))
    for certification in _dicts(parsed.get("certifications")):
        parts.append(_text(certification.get("name")))
    return "\n".join(part for part in parts if part.strip()).lower()


def _dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""
