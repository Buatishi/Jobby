import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.models.ats import ATSKeywordMatch, OptimizedCVSection
from app.services.ai_gateway import AIGateway, UserTier
from app.services.ats_analyzer.scoring import score_keyword_coverage
from app.services.match_engine.common import normalize_text


class _OptimizedPayload(BaseModel):
    sections: list[OptimizedCVSection] = Field(default_factory=list)


def _cv_sections(primary_cv: dict[str, Any]) -> dict[str, Any]:
    parsed_data = primary_cv.get("parsed_data")
    if isinstance(parsed_data, dict):
        return {
            "summary": parsed_data.get("summary"),
            "skills": parsed_data.get("skills", []),
            "experiences": parsed_data.get("experiences", []),
            "educations": parsed_data.get("educations", []),
            "certifications": parsed_data.get("certifications", []),
        }
    return {"raw_text": primary_cv.get("raw_text") or primary_cv.get("text") or ""}


def _low_coverage_keywords(matches: list[ATSKeywordMatch]) -> list[str]:
    return [
        match.keyword
        for match in matches
        if match.status in {"missing", "semantic"}
    ]


def _prompt(
    primary_cv: dict[str, Any],
    job: dict[str, Any],
    matches: list[ATSKeywordMatch],
) -> str:
    low_coverage = _low_coverage_keywords(matches)
    return (
        "Reescribi solamente las secciones del CV con baja cobertura ATS. "
        "No inventes experiencia, empresas, titulos, fechas ni tecnologias. "
        "Usa evidencia existente del CV y agrega keywords solo cuando sean "
        "defendibles por la experiencia del candidato.\n\n"
        "Devolve JSON valido con esta forma exacta:\n"
        '{"sections":[{"section_name":"string","original_excerpt":"string",'
        '"rewritten_text":"string","added_keywords":["string"],'
        '"rationale":"string"}]}\n\n'
        f"JOB:\n{json.dumps(job, ensure_ascii=False)}\n\n"
        f"LOW_COVERAGE_KEYWORDS:\n{json.dumps(low_coverage, ensure_ascii=False)}\n\n"
        f"CV_SECTIONS:\n{json.dumps(_cv_sections(primary_cv), ensure_ascii=False)}"
    )


def _parse_response(content: str) -> list[OptimizedCVSection]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Claude returned invalid CV optimizer JSON.") from exc
    try:
        return _OptimizedPayload.model_validate(parsed).sections
    except ValidationError as exc:
        raise ValueError("CV optimizer JSON failed validation.") from exc


def _mentions(text: str, keyword: str) -> bool:
    # Límite de palabra: la keyword "R" no debe encontrarse dentro de "React".
    needle = normalize_text(keyword)
    if not needle:
        return False
    pattern = rf"(?<!\w){re.escape(needle)}(?!\w)"
    return re.search(pattern, normalize_text(text)) is not None


def verify_sections(
    sections: list[OptimizedCVSection],
    matches: list[ATSKeywordMatch],
    cv_text: str,
) -> list[OptimizedCVSection]:
    """Separa las keywords con respaldo en el CV de las que la IA agregó sin él.

    Usa el reporte ATS ya calculado (literal y semántico tienen evidencia en el CV;
    ausente no), así que no hace llamadas a la IA ni pide vectores.
    """
    status_by_keyword = {
        normalize_text(match.keyword): match.status for match in matches
    }
    missing = [match.keyword for match in matches if match.status == "missing"]

    verified: list[OptimizedCVSection] = []
    for section in sections:
        text = section.rewritten_text
        unverified = {
            normalize_text(keyword): keyword
            for keyword in missing
            if _mentions(text, keyword)
        }
        added: list[str] = []
        for keyword in section.added_keywords:
            key = normalize_text(keyword)
            if key in unverified or not _mentions(text, keyword):
                # Ya marcada sin respaldo, o la IA la declaró pero no la escribió.
                continue
            status = status_by_keyword.get(key)
            backed_by_cv = _mentions(cv_text, keyword)
            if status == "missing" or (status is None and not backed_by_cv):
                unverified[key] = keyword
                continue
            added.append(keyword)
        verified.append(
            section.model_copy(
                update={
                    "added_keywords": added,
                    "unverified_keywords": list(unverified.values()),
                }
            )
        )
    return verified


def score_after_optimization(
    sections: list[OptimizedCVSection],
    matches: list[ATSKeywordMatch],
    penalty: int,
) -> int:
    """Puntaje ATS si se usan las secciones nuevas, contando solo lo verificado.

    Una keyword semántica que el texto nuevo nombra pasa a literal. Las ausentes
    siguen ausentes aunque el texto las mencione: no tienen respaldo en el CV.
    """
    rewritten = "\n".join(section.rewritten_text for section in sections)
    updated = [
        match.model_copy(update={"status": "literal"})
        if match.status == "semantic" and _mentions(rewritten, match.keyword)
        else match
        for match in matches
    ]
    return score_keyword_coverage(updated, penalty)


async def optimize_cv_sections(
    primary_cv: dict[str, Any],
    job: dict[str, Any],
    matches: list[ATSKeywordMatch],
    user_tier: UserTier,
    gateway: AIGateway | None = None,
) -> list[OptimizedCVSection]:
    missing_or_semantic = _low_coverage_keywords(matches)
    if not missing_or_semantic:
        return []

    ai_gateway = gateway or AIGateway()
    content = await ai_gateway.generate(
        "cv_optimization",
        user_tier,
        _prompt(primary_cv, job, matches),
        system=(
            "Actuas como especialista ATS y editor de CV. Respondes en espanol "
            "profesional, solo con JSON valido y sin markdown."
        ),
        json_mode=True,
    )
    cv_text = json.dumps(_cv_sections(primary_cv), ensure_ascii=False)
    return verify_sections(_parse_response(content), matches, cv_text)
