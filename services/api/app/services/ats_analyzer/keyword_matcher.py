import json
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from app.services.ai_gateway import AIGateway
from app.services.match_engine.common import cosine_similarity, normalize_text
from app.services.match_engine.s_languages import is_language_keyword
from app.services.skill_filter import skill_keywords
from app.services.skill_names import canonical_skill_key

KeywordStatus = Literal["literal", "semantic", "missing"]
Priority = Literal["required", "nice"]

# Cómo escribe la IA una palabra que el aviso presenta como deseable.
_NICE_WORDS = frozenset(
    {"nice", "nice_to_have", "preferred", "optional", "plus", "deseable"}
)

# Caracteres de contexto a cada lado de una palabra hallada en el resumen del CV.
SNIPPET_CONTEXT = 40

# Los vectores que ya existen para algunos términos del CV (los de las skills del
# perfil), por texto exacto. Se piden recién cuando hay que comparar por significado.
VectorLoader = Callable[[], Awaitable[Mapping[str, Sequence[float]]]]


@dataclass(frozen=True)
class KeywordMatch:
    keyword: str
    status: KeywordStatus
    matched_text: str | None = None
    priority: Priority = "required"


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
    for certification in parsed_data.get("certifications") or []:
        if isinstance(certification, dict):
            terms.append(str(certification.get("name") or ""))
    return [term for term in terms if term.strip()]


def _cv_summary(primary_cv: dict[str, Any]) -> str:
    """El resumen del CV, solo para buscar palabras literales (Decisión 42).

    Es un párrafo: sirve para ver si una palabra clave está escrita, pero no para
    comparar por significado (un vector del párrafo entero no se parece a una palabra).
    """
    parsed_data = primary_cv.get("parsed_data")
    summary = parsed_data.get("summary") if isinstance(parsed_data, dict) else None
    return summary.strip() if isinstance(summary, str) else ""


def _snippet(text: str, keyword: str) -> str:
    """El tramo del párrafo que rodea a la palabra, para mostrarlo en el reporte."""
    pattern = rf"(?<![\w+#]){re.escape(keyword)}(?![\w+#])"
    found = re.search(pattern, text, flags=re.IGNORECASE)
    if found is None:
        return keyword
    start, end = max(0, found.start() - SNIPPET_CONTEXT), found.end() + SNIPPET_CONTEXT
    cut = text[start:end].strip()
    return f"{'…' if start > 0 else ''}{cut}{'…' if end < len(text) else ''}"


def _job_text(job: dict[str, Any]) -> str:
    parts = [
        job.get("job_title") or "",
        " ".join(job.get("tech_stack") or []),
        " ".join(str(item) for item in (job.get("required_skills") or [])),
        job.get("raw_text") or "",
    ]
    return "\n".join(parts)


def _item_name(item: Any) -> str:
    """El nombre de una palabra clave que la IA devolvió como texto o como objeto."""
    if isinstance(item, dict):
        return str(item.get("name") or item.get("keyword") or "").strip()
    return str(item).strip()


def _item_priority(item: Any) -> Priority:
    if isinstance(item, dict):
        value = str(item.get("priority") or "").strip().lower()
        if value in _NICE_WORDS:
            return "nice"
    return "required"


def _keyword_items(content: str) -> list[Any] | None:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        values = parsed.get("keywords")
        return values if isinstance(values, list) else None
    return parsed if isinstance(parsed, list) else None


def _parse_priorities(content: str) -> dict[str, Priority]:
    """Las palabras que la IA marcó como deseables, por palabra en minúsculas."""
    return {
        name.lower(): "nice"
        for item in _keyword_items(content) or []
        if (name := _item_name(item)) and _item_priority(item) == "nice"
    }


def _parse_keywords(content: str, job: dict[str, Any]) -> list[str]:
    items = _keyword_items(content)
    if items is not None:
        return sorted({name for item in items if (name := _item_name(item))})

    fallback = [str(item) for item in job.get("required_skills") or []]
    fallback.extend(str(item) for item in job.get("tech_stack") or [])
    return sorted({item.strip() for item in fallback if item.strip()})


async def extract_job_keywords(
    job: dict[str, Any],
    gateway: AIGateway | None = None,
) -> list[str]:
    keywords, _priorities = await extract_job_keyword_priorities(job, gateway)
    return keywords


async def extract_job_keyword_priorities(
    job: dict[str, Any],
    gateway: AIGateway | None = None,
) -> tuple[list[str], dict[str, Priority]]:
    """Las palabras clave del puesto y cuáles el aviso presenta como deseables."""
    ai_gateway = gateway or AIGateway()
    content = await ai_gateway.generate(
        "match_reasoning",
        "free",
        (
            "Extraé las habilidades que pide este job para filtrar CVs con un ATS. "
            "Devolvé JSON estricto con forma "
            '{"keywords": [{"name": "Python", "priority": "required"}, '
            '{"name": "Docker", "priority": "nice"}]}. priority es "required" salvo '
            'que el aviso presente la habilidad como deseable ("nice to have", "plus", '
            '"preferred", "se valora", "deseable", "valorable"): ahí es "nice". '
            "Incluí solo habilidades: lenguajes, "
            "frameworks, librerías, herramientas, plataformas, metodologías y "
            "certificaciones, cada una con su nombre corto y común "
            '("SQL", no "Escritura de consultas SQL"). No incluyas idiomas (se '
            "evalúan aparte), el título del puesto, el nivel o seniority, la "
            "modalidad (remoto, híbrido, presencial), el tipo de jornada, la ciudad o "
            "el país, la empresa, ni tareas o responsabilidades escritas como "
            f"frases.\n\n{_job_text(job)}"
        ),
        system="Sos un extractor ATS. Respondé solo JSON válido.",
        json_mode=True,
    )
    return _parse_keywords(content, job), _parse_priorities(content)


async def classify_keyword_priorities(
    job: dict[str, Any],
    keywords: list[str],
    gateway: AIGateway | None = None,
) -> dict[str, str]:
    """De unas palabras ya extraídas, cuáles el aviso presenta como deseables.

    Sirve para un reporte guardado antes de que se guardara la prioridad. Cualquier
    falla deja a todas como obligatorias: es el comportamiento de antes.
    """
    if not keywords:
        return {}
    try:
        content = await (gateway or AIGateway()).generate(
            "match_reasoning",
            "free",
            (
                "De estas habilidades de un aviso, indicá cuáles el aviso presenta "
                "como "
                'deseables ("nice to have", "plus", "preferred", "se valora", '
                '"deseable", "valorable") y no como requisito. Devolvé JSON estricto '
                'con forma {"nice": ["Docker"]}, con los nombres tal como figuran en '
                f'la lista; si ninguna es deseable, {{"nice": []}}.\n\n'
                f"HABILIDADES: {json.dumps(keywords, ensure_ascii=False)}\n\n"
                f"AVISO:\n{_job_text(job)}"
            ),
            system="Sos un extractor ATS. Respondé solo JSON válido.",
            json_mode=True,
        )
        parsed = json.loads(content)
    except Exception:
        return {}
    names = parsed.get("nice") if isinstance(parsed, dict) else None
    known = {keyword.strip().lower() for keyword in keywords}
    return {
        name.strip().lower(): "nice"
        for name in names or []
        if isinstance(name, str) and name.strip().lower() in known
    }


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


def _contains_whole_word(text: str, keyword: str) -> bool:
    """¿`keyword` aparece en `text` como palabra completa (los dos en minúsculas)?

    «Git» no está en «Digital», ni «SQL» en «PostgreSQL», ni «C» en «C++»: a los lados
    no puede haber una letra, un número, `+` ni `#`. Un punto sí: cierra una oración.
    """
    if not keyword:
        return False
    pattern = rf"(?<![\w+#]){re.escape(keyword)}(?![\w+#])"
    return re.search(pattern, text) is not None


async def analyze_keywords(
    job: dict[str, Any],
    primary_cv: dict[str, Any],
    gateway: AIGateway | None = None,
    semantic_threshold: float = 0.75,
    *,
    keywords: list[str] | None = None,
    priorities: Mapping[str, str] | None = None,
    saved_vectors: VectorLoader | None = None,
) -> ATSKeywordResult:
    """`keywords` son las que el puesto ya tiene guardadas: con ellas no se consulta a
    la IA, que daría otras cada vez. Las de la IA y las guardadas pasan por el mismo
    filtro: solo cuentan las habilidades (`skill_filter`). `priorities` dice cuáles son
    deseables (por palabra en minúsculas); sin ellas, todas son obligatorias."""
    ai_gateway = gateway or AIGateway()
    if keywords is None:
        keywords, priorities = await extract_job_keyword_priorities(job, ai_gateway)
    nice = {key for key, value in (priorities or {}).items() if value == "nice"}
    keywords = skill_keywords(keywords, job)
    # Los idiomas se evalúan como requisito del puesto: en la lista de palabras clave
    # se contaban dos veces y se contradecían (Decisión 42).
    keywords = [keyword for keyword in keywords if not is_language_keyword(keyword)]
    cv_terms = _cv_terms(primary_cv)
    summary = _cv_summary(primary_cv)
    normalized_summary = normalize_text(summary)
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
                if _contains_whole_word(normalized, normalized_keyword)
            ),
            None,
        )
        literal = literal or cv_by_key.get(canonical_skill_key(keyword))
        if literal is None and _contains_whole_word(
            normalized_summary, normalized_keyword
        ):
            literal = _snippet(summary, keyword)
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
        priority: Priority = "nice" if keyword.strip().lower() in nice else "required"
        if keyword in literals:
            matches.append(
                KeywordMatch(keyword, "literal", literals[keyword], priority)
            )
        elif keyword in semantic:
            matches.append(
                KeywordMatch(keyword, "semantic", semantic[keyword], priority)
            )
        else:
            matches.append(KeywordMatch(keyword, "missing", None, priority))

    return ATSKeywordResult(keywords=keywords, matches=matches)
