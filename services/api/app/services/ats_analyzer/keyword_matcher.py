import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from app.services.ai_gateway import AIGateway
from app.services.match_engine.common import cosine_similarity, normalize_text
from app.services.skill_names import canonical_skill_key

KeywordStatus = Literal["literal", "semantic", "missing"]

# Los vectores que ya existen para algunos términos del CV (los de las skills del
# perfil), por texto exacto. Se piden recién cuando hay que comparar por significado.
VectorLoader = Callable[[], Awaitable[Mapping[str, Sequence[float]]]]


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
    saved_vectors: VectorLoader | None = None,
) -> dict[str, str]:
    """Primer término del CV parecido a cada keyword que no apareció literal.

    Pide los vectores en dos lotes: antes se pedía uno por palabra y los del CV se
    repetían por cada keyword faltante (10 faltantes y 40 términos: 410 llamadas). Los
    términos que ya tienen vector guardado no entran al segundo lote: el mismo modelo
    sobre el mismo texto da el mismo vector, así que el resultado no cambia.
    """
    if not keywords or not cv_terms:
        return {}

    keyword_vectors = await gateway.embed_many(keywords)
    known = await _usable_saved_vectors(saved_vectors, keyword_vectors)
    missing = list(dict.fromkeys(term for term in cv_terms if term not in known))
    requested = await gateway.embed_many(missing) if missing else []
    fresh = dict(zip(missing, requested, strict=True))
    term_vectors = [known[term] if term in known else fresh[term] for term in cv_terms]

    matches: dict[str, str] = {}
    for keyword, keyword_vector in zip(keywords, keyword_vectors, strict=True):
        for term, term_vector in zip(cv_terms, term_vectors, strict=True):
            if cosine_similarity(keyword_vector, term_vector) >= threshold:
                matches[keyword] = term
                break
    return matches


async def _usable_saved_vectors(
    loader: VectorLoader | None,
    keyword_vectors: Sequence[Sequence[float]],
) -> Mapping[str, Sequence[float]]:
    """Solo los guardados con el mismo tamaño que los recién pedidos: otro tamaño es de
    otro modelo y compararlo daría 0 sin avisar."""
    if loader is None or not keyword_vectors:
        return {}
    size = len(keyword_vectors[0])
    return {
        term: vector for term, vector in (await loader()).items() if len(vector) == size
    }


async def analyze_keywords(
    job: dict[str, Any],
    primary_cv: dict[str, Any],
    gateway: AIGateway | None = None,
    semantic_threshold: float = 0.75,
    *,
    keywords: list[str] | None = None,
    saved_vectors: VectorLoader | None = None,
) -> ATSKeywordResult:
    """`keywords` son las que el puesto ya tiene guardadas: con ellas no se consulta a
    la IA, que daría otras cada vez."""
    ai_gateway = gateway or AIGateway()
    if keywords is None:
        keywords = await extract_job_keywords(job, ai_gateway)
    cv_terms = _cv_terms(primary_cv)
    normalized_cv = {normalize_text(term): term for term in cv_terms}
    # Un alias o una traducción también es literal: «Integración de APIs» es
    # «API Integrations». Se mira después de la búsqueda de siempre.
    cv_by_key: dict[str, str] = {}
    for term in cv_terms:
        key = canonical_skill_key(term)
        if key:
            cv_by_key.setdefault(key, term)
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
        literal = literal or cv_by_key.get(canonical_skill_key(keyword))
        if literal:
            literals[keyword] = literal

    pending = [keyword for keyword in keywords if keyword not in literals]
    semantic = await _semantic_matches(
        pending,
        cv_terms,
        ai_gateway,
        semantic_threshold,
        saved_vectors,
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
