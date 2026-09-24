import json
from dataclasses import dataclass
from typing import Any, Literal

from app.services.ai_gateway import AIGateway
from app.services.match_engine.common import cosine_similarity, normalize_text

KeywordStatus = Literal["literal", "semantic", "missing"]


@dataclass(frozen=True)
class KeywordMatch:
    keyword: str
    status: KeywordStatus
    matched_text: str | None = None


@dataclass(frozen=True)
class ATSKeywordResult:
    keywords: list[str]
    matches: list[KeywordMatch]


def _cv_terms(primary_cv: dict[str, Any]) -> list[str]:
    parsed_data = primary_cv.get("parsed_data")
    if not isinstance(parsed_data, dict):
        return []

    terms: list[str] = []
    for skill in parsed_data.get("skills") or []:
        if isinstance(skill, dict):
            terms.append(str(skill.get("name") or ""))
        else:
            terms.append(str(skill))
    for experience in parsed_data.get("experiences") or []:
        if isinstance(experience, dict):
            terms.append(str(experience.get("title") or ""))
            terms.append(str(experience.get("description") or ""))
            achievements = experience.get("achievements") or []
            if isinstance(achievements, list):
                terms.extend(str(item) for item in achievements)
    for education in parsed_data.get("educations") or []:
        if isinstance(education, dict):
            terms.append(str(education.get("field_of_study") or ""))
            terms.append(str(education.get("degree_level") or ""))
    return [term for term in terms if term.strip()]


def _job_text(job: dict[str, Any]) -> str:
    parts = [
        job.get("job_title") or "",
        " ".join(job.get("tech_stack") or []),
        " ".join(str(item) for item in (job.get("required_skills") or [])),
        job.get("raw_text") or "",
    ]
    return "\n".join(parts)


def _parse_keywords(content: str, job: dict[str, Any]) -> list[str]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        values = parsed.get("keywords")
        if isinstance(values, list):
            return sorted({str(item).strip() for item in values if str(item).strip()})
    if isinstance(parsed, list):
        return sorted({str(item).strip() for item in parsed if str(item).strip()})

    fallback = [str(item) for item in job.get("required_skills") or []]
    fallback.extend(str(item) for item in job.get("tech_stack") or [])
    return sorted({item.strip() for item in fallback if item.strip()})


async def extract_job_keywords(
    job: dict[str, Any],
    gateway: AIGateway | None = None,
) -> list[str]:
    ai_gateway = gateway or AIGateway()
    content = await ai_gateway.generate(
        "match_reasoning",
        "free",
        (
            "Extraé keywords ATS concretas de este job. Devolvé JSON estricto "
            'con forma {"keywords": ["Python", "React"]}. Incluí skills, '
            "frameworks, herramientas, seniority, idiomas y títulos requeridos.\n\n"
            f"{_job_text(job)}"
        ),
        system="Sos un extractor ATS. Respondé solo JSON válido.",
        json_mode=True,
    )
    return _parse_keywords(content, job)


async def _semantic_matches(
    keywords: list[str],
    cv_terms: list[str],
    gateway: AIGateway,
    threshold: float,
) -> dict[str, str]:
    """Primer término del CV parecido a cada keyword que no apareció literal.

    Pide los vectores en dos lotes: antes se pedía uno por palabra y los del CV se
    repetían por cada keyword faltante (10 faltantes y 40 términos: 410 llamadas).
    """
    if not keywords or not cv_terms:
        return {}

    keyword_vectors = await gateway.embed_many(keywords)
    term_vectors = await gateway.embed_many(cv_terms)
    matches: dict[str, str] = {}
    for keyword, keyword_vector in zip(keywords, keyword_vectors, strict=True):
        for term, term_vector in zip(cv_terms, term_vectors, strict=True):
            if cosine_similarity(keyword_vector, term_vector) >= threshold:
                matches[keyword] = term
                break
    return matches


async def analyze_keywords(
    job: dict[str, Any],
    primary_cv: dict[str, Any],
    gateway: AIGateway | None = None,
    semantic_threshold: float = 0.75,
) -> ATSKeywordResult:
    ai_gateway = gateway or AIGateway()
    keywords = await extract_job_keywords(job, ai_gateway)
    cv_terms = _cv_terms(primary_cv)
    normalized_cv = {normalize_text(term): term for term in cv_terms}
    literals: dict[str, str] = {}
    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        literal = next(
            (
                original
                for normalized, original in normalized_cv.items()
                if normalized_keyword == normalized or normalized_keyword in normalized
            ),
            None,
        )
        if literal:
            literals[keyword] = literal

    pending = [keyword for keyword in keywords if keyword not in literals]
    semantic = await _semantic_matches(
        pending,
        cv_terms,
        ai_gateway,
        semantic_threshold,
    )

    matches: list[KeywordMatch] = []
    for keyword in keywords:
        if keyword in literals:
            matches.append(KeywordMatch(keyword, "literal", literals[keyword]))
        elif keyword in semantic:
            matches.append(KeywordMatch(keyword, "semantic", semantic[keyword]))
        else:
            matches.append(KeywordMatch(keyword, "missing"))

    return ATSKeywordResult(keywords=keywords, matches=matches)
