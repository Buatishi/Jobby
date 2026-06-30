import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.models.ats import ATSKeywordMatch, OptimizedCVSection
from app.services.ai_gateway import AIGateway


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


async def optimize_cv_sections(
    primary_cv: dict[str, Any],
    job: dict[str, Any],
    matches: list[ATSKeywordMatch],
    gateway: AIGateway | None = None,
) -> list[OptimizedCVSection]:
    missing_or_semantic = _low_coverage_keywords(matches)
    if not missing_or_semantic:
        return []

    ai_gateway = gateway or AIGateway()
    content = await ai_gateway.generate(
        "cv_optimization",
        "premium",
        _prompt(primary_cv, job, matches),
        system=(
            "Actuas como especialista ATS y editor de CV. Respondes en espanol "
            "profesional, solo con JSON valido y sin markdown."
        ),
        json_mode=True,
    )
    return _parse_response(content)
