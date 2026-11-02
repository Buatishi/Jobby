from typing import Any

from app.services.match_engine.common import skill_key
from app.services.reality_gap.documents import (
    DocumentSide,
    mentions,
    read_side,
)


def build_reality_gap(
    saved_skills: list[dict[str, Any]],
    rejected_skills: list[dict[str, Any]],
    cv_document: dict[str, Any] | None,
    linkedin_document: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compara lo que dice el CV con lo que dice el PDF de LinkedIn, skill por skill.

    Se comparan las skills guardadas del perfil (confirmadas o no: son las que usa el
    motor de comparación) y las que nombra algún documento aunque no estén guardadas,
    como las que solo figuran en LinkedIn. Las marcas `in_cv` e `in_linkedin` de las
    filas no se usan: solo se ponen en verdadero y nunca se apagan, así que una skill
    sacada del CV seguía contando. Solo el CV leído antes de que se guardara su lista
    propia las usa, porque no hay otra cosa.

    Las filas de `skills` se repiten (el parseo del CV guarda la misma skill con otra
    categoría cada vez), por eso se agrupan por su forma común (`skill_key`). Sin los
    dos documentos leídos no hay con qué comparar: las skills se listan sin puntaje.
    """
    cv = read_side(cv_document, "extracted_skills", fallback_ok=True)
    linkedin = read_side(linkedin_document, "skills", fallback_ok=False)
    comparable = cv is not None and linkedin is not None

    rejected_keys = {skill_key(skill.get("name")) for skill in rejected_skills}
    rejected_keys.discard("")

    groups: dict[str, list[dict[str, Any]]] = {}
    for skill in saved_skills:
        key = skill_key(skill.get("name"))
        if key:
            groups.setdefault(key, []).append(skill)

    keys = dict.fromkeys(groups)
    for side in (cv, linkedin):
        if side is not None and side.named:
            keys.update(dict.fromkeys(side.named))

    results = [
        _compare(key, groups.get(key, []), rejected_keys, cv, linkedin, comparable)
        for key in keys
    ]
    results.sort(key=_order)
    return {
        "skills": results,
        "summary": _summary(results, comparable),
        "cv": _document_info(cv_document, cv),
        "linkedin": _document_info(linkedin_document, linkedin),
    }


def _compare(
    key: str,
    rows: list[dict[str, Any]],
    rejected_keys: set[str],
    cv: DocumentSide | None,
    linkedin: DocumentSide | None,
    comparable: bool,
) -> dict[str, Any]:
    in_cv_entry = cv.named.get(key) if cv is not None and cv.named else None
    in_linkedin_entry = (
        linkedin.named.get(key) if linkedin is not None and linkedin.named else None
    )
    shown = (
        _row_that_names_the_group(rows)
        if rows
        else (in_cv_entry or in_linkedin_entry or {})
    )
    name = str(shown.get("name") or "")
    category = shown.get("category") or next(
        (
            entry["category"]
            for entry in (in_cv_entry, in_linkedin_entry)
            if entry and entry["category"]
        ),
        None,
    )
    names = {str(row.get("name") or "") for row in rows}
    names.update(entry["name"] for entry in (in_cv_entry, in_linkedin_entry) if entry)
    # «Microsoft Excel» se busca también como «excel», que es como lo escribe el texto.
    # Una forma común de varias palabras no: «api» y «rest» sueltas no son «API REST».
    if " " not in key:
        names.add(key)

    confirmed = any(bool(row.get("confirmed")) for row in rows)
    in_cv = _present(
        cv,
        in_cv_entry,
        names,
        saved_mark=any(bool(row.get("in_cv")) for row in rows),
    )
    in_linkedin = _present(linkedin, in_linkedin_entry, names, saved_mark=False)
    # Rechazar una skill en una revisión vieja del asistente no pesa si después se
    # confirmó: es lo último que la persona decidió.
    rejected = key in rejected_keys and not confirmed

    score: int | None = None
    if comparable:
        score = (
            (40 if in_cv else 0) + (40 if in_linkedin else 0) + (0 if rejected else 20)
        )
    return {
        "skill_id": shown.get("id"),
        "name": name,
        "category": category,
        "in_cv": in_cv,
        "in_linkedin": in_linkedin,
        "saved": bool(rows),
        "confirmed": confirmed,
        "rejected": rejected,
        "coherence_score": score,
        "recommendation": _recommendation(
            name, in_cv, in_linkedin, rejected, comparable
        ),
    }


def _present(
    side: DocumentSide | None,
    entry: dict[str, Any] | None,
    names: set[str],
    *,
    saved_mark: bool,
) -> bool | None:
    """¿Está la skill en el documento? `None` si el documento falta o no se leyó."""
    if side is None:
        return None
    if entry is not None or mentions(side, names):
        return True
    return side.named is None and saved_mark


def _row_that_names_the_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """La fila que da nombre, categoría e id: la confirmada, o el nombre más corto.

    El nombre más corto evita «Microsoft Power BI» sobre «Power BI» sin inventar un
    nombre que ninguna fila tenga.
    """

    def order(row: dict[str, Any]) -> tuple[bool, int, str]:
        name = str(row.get("name") or "")
        return (not row.get("confirmed"), len(name), name.casefold())

    return min(rows, key=order)


def _order(item: dict[str, Any]) -> tuple[int, str]:
    score = item["coherence_score"]
    return (0 if score is None else score, item["name"].casefold())


def _summary(results: list[dict[str, Any]], comparable: bool) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "comparable": comparable,
        "total": len(results),
        "in_both": 0,
        "only_cv": 0,
        "only_linkedin": 0,
        "in_neither": 0,
        "score": None,
    }
    if not comparable:
        return summary
    for item in results:
        if item["in_cv"] and item["in_linkedin"]:
            summary["in_both"] += 1
        elif item["in_cv"]:
            summary["only_cv"] += 1
        elif item["in_linkedin"]:
            summary["only_linkedin"] += 1
        else:
            summary["in_neither"] += 1
    if results:
        summary["score"] = round(
            sum(item["coherence_score"] for item in results) / len(results)
        )
    return summary


def _document_info(
    document: dict[str, Any] | None,
    side: DocumentSide | None,
) -> dict[str, Any] | None:
    if document is None:
        return None
    created_at = document.get("created_at")
    source = None
    if side is not None:
        source = "saved" if side.named is None else "document"
    return {
        "filename": document.get("original_filename"),
        "uploaded_at": str(created_at) if created_at else None,
        "status": document.get("status"),
        "skills_source": source,
    }


def _recommendation(
    name: str,
    in_cv: bool | None,
    in_linkedin: bool | None,
    rejected: bool,
    comparable: bool,
) -> str | None:
    if rejected:
        return f"Revisá si {name} debe volver al perfil o quedar rechazada."
    if not comparable:
        return None
    if not in_cv and in_linkedin:
        return f"Agregá {name} al CV para alinear tus canales."
    if in_cv and not in_linkedin:
        return f"Agregá {name} a LinkedIn."
    if not in_cv and not in_linkedin:
        return f"Mostrá evidencia de {name} en CV y LinkedIn."
    return None
