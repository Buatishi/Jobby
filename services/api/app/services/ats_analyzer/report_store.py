"""Qué se guarda del reporte ATS y cuándo sigue valiendo (Decisión 33).

Todo lo de acá es opcional para el resultado: si la tabla todavía no existe (la
migración 031 sin aplicar) o la base falla, la lectura devuelve «no hay nada guardado» y
la escritura se omite con un aviso. El reporte se calcula como antes; lo único que se
pierde es el ahorro.

Cada puesto tiene una sola fila: su último reporte. Las keywords del puesto son las del
reporte (`keyword_matches[].keyword`), así que no hay otro lugar donde guardarlas: al
recalcular tras cambiar el CV se reutilizan las de la fila anterior.
"""

import hashlib
import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from app.models.ats import ATSFormatIssue, ATSKeywordMatch, ATSReport
from app.services.ats_analyzer.format_checker import format_was_evaluated
from app.services.ats_analyzer.keyword_matcher import VectorLoader
from app.services.match_engine.common import parse_embedding

logger = logging.getLogger(__name__)

# Se sube al cambiar cómo se calcula el reporte (reglas de coincidencia, umbral,
# pesos): lo guardado con la regla vieja deja de servirse y se recalcula en la próxima
# apertura. La 2 es la primera con el formato del PDF leído de verdad (Decisión 34): la
# 1 daba siempre «sin problemas de formato».
ATS_REPORT_VERSION = 2


def cv_fingerprint(primary_cv: Mapping[str, Any]) -> str:
    """Huella de los datos del CV de los que depende el reporte.

    El reporte solo lee `parsed_data`. Se usa su contenido y no `updated_at` porque
    releer el mismo documento reemplaza `parsed_data` sin tocar esa fecha.
    """
    canonical = json.dumps(
        primary_cv.get("parsed_data"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


async def fetch_report_row(
    supabase: Any, job_id: str, user_id: str
) -> dict[str, Any] | None:
    try:
        response = await (
            supabase.table("ats_reports")
            .select("*")
            .eq("job_id", job_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.warning("No se pudo leer el reporte ATS guardado: %s", exc)
        return None
    data = getattr(response, "data", None)
    return data if isinstance(data, dict) else None


def report_from_row(
    row: Mapping[str, Any] | None,
    job_id: str,
    primary_cv: Mapping[str, Any],
) -> ATSReport | None:
    """El reporte guardado, solo si sigue valiendo para el CV principal de hoy."""
    if row is None:
        return None
    if row.get("report_version") != ATS_REPORT_VERSION:
        return None
    if str(row.get("cv_document_id")) != str(primary_cv.get("id")):
        return None
    if row.get("cv_fingerprint") != cv_fingerprint(primary_cv):
        return None

    matches = row.get("keyword_matches")
    issues = row.get("format_issues")
    if not isinstance(matches, list) or not isinstance(issues, list):
        return None
    try:
        return ATSReport(
            job_id=job_id,
            ats_score=int(row["ats_score"]),
            keyword_matches=[ATSKeywordMatch.model_validate(item) for item in matches],
            format_issues=[ATSFormatIssue.model_validate(item) for item in issues],
            # No se guarda: sale del CV principal, que la huella ya comprobó que es el
            # mismo.
            format_evaluated=format_was_evaluated(dict(primary_cv)),
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        # Una fila dañada no debe romper el reporte: se recalcula y se reemplaza.
        return None


async def save_report(
    supabase: Any,
    user_id: str,
    primary_cv: Mapping[str, Any],
    report: ATSReport,
) -> None:
    if not primary_cv.get("id"):
        return
    row = {
        "job_id": report.job_id,
        "user_id": user_id,
        "cv_document_id": primary_cv["id"],
        "cv_fingerprint": cv_fingerprint(primary_cv),
        "report_version": ATS_REPORT_VERSION,
        "ats_score": report.ats_score,
        "keyword_matches": [item.model_dump() for item in report.keyword_matches],
        "format_issues": [item.model_dump() for item in report.format_issues],
        "computed_at": datetime.now(UTC).isoformat(),
    }
    try:
        await supabase.table("ats_reports").upsert(row, on_conflict="job_id").execute()
    except Exception as exc:
        logger.warning("No se pudo guardar el reporte ATS: %s", exc)


def keywords_from_row(row: Mapping[str, Any] | None) -> list[str] | None:
    """Las keywords del puesto, tal como las dejó el último reporte, aunque ya no valga.

    Salen de una IA y cambian en cada consulta: reutilizarlas es lo que mantiene al
    puesto con las mismas entre aperturas y entre recálculos.
    """
    if row is None:
        return None
    matches = row.get("keyword_matches")
    if not isinstance(matches, list):
        return None
    keywords = [
        item["keyword"]
        for item in matches
        if isinstance(item, dict)
        and isinstance(item.get("keyword"), str)
        and item["keyword"].strip()
    ]
    return keywords or None


def skill_vector_loader(
    supabase: Any, primary_cv: Mapping[str, Any]
) -> VectorLoader | None:
    """Los vectores que las skills del perfil ya guardan, por nombre exacto.

    Se leen solo si hace falta (hay keywords sin coincidencia literal). Las skills que
    la persona agregó a mano no tienen vector y quedan fuera: esas se piden igual.
    """
    profile_id = primary_cv.get("profile_id")
    if not profile_id:
        return None

    async def load() -> dict[str, list[float]]:
        try:
            response = await (
                supabase.table("skills")
                .select("name,embedding")
                .eq("profile_id", profile_id)
                .execute()
            )
        except Exception as exc:
            logger.warning("No se pudieron leer los vectores de las skills: %s", exc)
            return {}
        rows = getattr(response, "data", None)
        vectors: dict[str, list[float]] = {}
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                continue
            try:
                vector = parse_embedding(row.get("embedding"))
            except ValueError:
                continue
            if vector:
                vectors.setdefault(row["name"], vector)
        return vectors

    return load
