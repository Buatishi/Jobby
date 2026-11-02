import json
import logging
import re
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.models.ats import ATSKeywordMatch, ATSRequirement, OptimizedCVSection
from app.services.ai_gateway import AIGateway, UserTier
from app.services.ai_gateway.errors import ProviderUnavailableError
from app.services.ai_gateway.prompts.untrusted import UNTRUSTED_DATA_NOTICE_ES
from app.services.ats_analyzer.scoring import compose_ats_score
from app.services.cv_parser import strip_embeddings
from app.services.match_engine.common import normalize_text
from app.services.skill_names import canonical_skill_key
from app.services.text_quality import fold

logger = logging.getLogger("jobmatch.ats")

OPTIMIZER_SYSTEM = (
    "Actuas como especialista ATS y editor de CV. Respondes en espanol "
    "profesional, solo con JSON valido y sin markdown."
)


class _OptimizedPayload(BaseModel):
    sections: list[OptimizedCVSection] = Field(default_factory=list)


# Una keyword de menos letras que esto («Go», «R», «AI») no se busca por palabras
# equivalentes: coincidiría con cualquier texto.
MIN_EQUIVALENCE_LENGTH = 5
_EXPERIENCE_ID = re.compile(r"^exp-(\d+)$")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?;])\s+|\n+")


def _cv_sections(primary_cv: dict[str, Any]) -> dict[str, Any]:
    parsed_data = primary_cv.get("parsed_data")
    if isinstance(parsed_data, dict):
        skills = parsed_data.get("skills", [])
        return {
            "summary": parsed_data.get("summary"),
            # Los CV guardados antes de cortar la fuga traen el vector de 1536
            # números en cada skill: no va al prompt ni al texto de verificación.
            "skills": strip_embeddings(skills) if isinstance(skills, list) else skills,
            "experiences": _with_ids(parsed_data.get("experiences", [])),
            "educations": parsed_data.get("educations", []),
            "certifications": parsed_data.get("certifications", []),
        }
    return {"raw_text": primary_cv.get("raw_text") or primary_cv.get("text") or ""}


def _with_ids(experiences: Any) -> Any:
    """Cada experiencia con un id («exp-1»…) para que la IA diga a cuál se refiere."""
    if not isinstance(experiences, list):
        return experiences
    return [
        {"id": f"exp-{index}", **item} if isinstance(item, dict) else item
        for index, item in enumerate(experiences, start=1)
    ]


def _low_coverage_keywords(matches: list[ATSKeywordMatch]) -> list[str]:
    return [
        match.keyword for match in matches if match.status in {"missing", "semantic"}
    ]


def declared_keywords(
    matches: Sequence[ATSKeywordMatch], confirmed: Sequence[str]
) -> list[str]:
    """Las keywords que la persona declaró saber y el reporte da por faltantes.

    Se devuelve el nombre tal como figura en el reporte, y solo las que el reporte
    marca ausentes: lo que llega del navegador no puede meter texto propio en el
    pedido a la IA ni en el CV.
    """
    wanted = {normalize_text(keyword) for keyword in confirmed}
    return [
        match.keyword
        for match in matches
        if match.status == "missing" and normalize_text(match.keyword) in wanted
    ]


def _declared_block(declared: Sequence[str]) -> str:
    if not declared:
        return ""
    return (
        "DECLARED_KEYWORDS (el candidato declaro que las sabe aunque su CV no lo "
        "muestre: escribilas como habilidades en la seccion skills, sumandolas a la "
        "lista, y si queda natural nombralas en summary. No las pongas dentro de una "
        "experiencia ni inventes cargos, empresas, fechas, proyectos o logros con "
        f"ellas):\n{json.dumps(list(declared), ensure_ascii=False)}\n\n"
    )


def _prompt(
    primary_cv: dict[str, Any],
    job: dict[str, Any],
    matches: list[ATSKeywordMatch],
    declared: Sequence[str] = (),
) -> str:
    low_coverage = _low_coverage_keywords(matches)
    # La fila del puesto se lee con select("*") y trae su vector (`embedding`):
    # ~15 KB de números que el modelo no usa y que se pagan en tokens.
    prompt_job = strip_embeddings([job])[0]
    return (
        f"{UNTRUSTED_DATA_NOTICE_ES}\n\n"
        "Reescribi solamente las secciones del CV con baja cobertura ATS. "
        "No inventes experiencia, empresas, titulos, fechas ni tecnologias. "
        "Usa evidencia existente del CV y agrega keywords solo cuando sean "
        "defendibles por la experiencia del candidato. "
        "section_name tiene que ser una de estas claves: summary, skills, "
        "experiences, educations o certifications. original_excerpt copia "
        "textual el fragmento del CV que se reemplaza. Cada experiencia de "
        "CV_SECTIONS tiene un id: en una seccion experiences, target_id es el id "
        "de esa experiencia, original_excerpt copia solo sus vinetas (una por "
        "renglon, sin cargo, empresa ni fechas) y rewritten_text son las vinetas "
        "nuevas (una por renglon, sin cargo, empresa ni fechas). En las demas "
        "secciones target_id va vacio.\n\n"
        "Devolve JSON valido con esta forma exacta:\n"
        '{"sections":[{"section_name":"string","target_id":"string",'
        '"original_excerpt":"string","rewritten_text":"string",'
        '"added_keywords":["string"],"rationale":"string"}]}\n\n'
        f"JOB:\n{json.dumps(prompt_job, ensure_ascii=False)}\n\n"
        f"LOW_COVERAGE_KEYWORDS:\n{json.dumps(low_coverage, ensure_ascii=False)}\n\n"
        f"{_declared_block(declared)}"
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


def _words(text: str) -> str:
    """Las palabras de un texto sin acentos, mayúsculas ni signos, entre espacios."""
    return f" {' '.join(re.findall(r'[^\W_]+', fold(text)))} "


def _supported_by_cv(keyword: str, evidence: Sequence[str]) -> bool:
    """¿Algún texto del CV dice lo mismo que la keyword con otras palabras?

    Compara las palabras ya llevadas a su forma común (`canonical_skill_key`: «prueba» y
    «testing», «diseño» y «design», «desarrollo» y «development»): todas las de la
    keyword tienen que estar en el mismo texto del CV, en cualquier orden. «Testing»
    está respaldada por «casos de prueba documentados»; «LangChain» no lo está por
    nada. Una keyword muy corta no se busca así: coincidiría con cualquier cosa.
    """
    words = set(canonical_skill_key(keyword).split())
    if not words or sum(len(word) for word in words) < MIN_EQUIVALENCE_LENGTH:
        return False
    return any(words <= set(canonical_skill_key(text).split()) for text in evidence)


def _sentences(text: str) -> list[str]:
    """Un párrafo en oraciones: una keyword se respalda dentro de una oración, no
    juntando palabras sueltas de un párrafo entero («API» de una y «diseño» de otra)."""
    return [part.strip() for part in _SENTENCE_BREAK.split(text) if part.strip()]


def evidence_texts(primary_cv: dict[str, Any]) -> list[str]:
    """Los textos del CV con los que se comprueba una keyword (sin claves ni JSON)."""
    sections = _cv_sections(primary_cv)
    texts: list[str] = _sentences(str(sections.get("summary") or ""))
    for skill in sections.get("skills") or []:
        texts.append(
            str(skill.get("name") or "") if isinstance(skill, dict) else str(skill)
        )
    for experience in sections.get("experiences") or []:
        if isinstance(experience, dict):
            texts.append(str(experience.get("title") or ""))
            texts.extend(_sentences(str(experience.get("description") or "")))
            achievements = experience.get("achievements") or []
            if isinstance(achievements, list):
                texts.extend(str(item) for item in achievements)
    for education in sections.get("educations") or []:
        if isinstance(education, dict):
            texts.append(str(education.get("field_of_study") or ""))
    for certification in sections.get("certifications") or []:
        if isinstance(certification, dict):
            texts.append(str(certification.get("name") or ""))
    return [text for text in texts if text.strip()]


def attach_targets(
    sections: list[OptimizedCVSection], primary_cv: dict[str, Any]
) -> list[OptimizedCVSection]:
    """A cada sección `experiences`, la experiencia del CV a la que se refiere.

    Se toma el `target_id` que devolvió la IA; si falta o no existe, se busca la
    experiencia cuyo cargo (y empresa) aparecen en el fragmento: la IA suele copiarlo
    como «Cargo | Empresa | fechas…». Sin una única candidata no se adivina.
    """
    experiences = [
        item
        for item in _cv_sections(primary_cv).get("experiences") or []
        if isinstance(item, dict)
    ]
    resolved: list[OptimizedCVSection] = []
    for section in sections:
        index = (
            _target_index(section, experiences)
            if section.section_name == "experiences"
            else None
        )
        if index is None:
            resolved.append(section)
            continue
        experience = experiences[index]
        resolved.append(
            section.model_copy(
                update={
                    "target_id": str(experience.get("id") or ""),
                    "target_company": str(experience.get("company") or ""),
                    "target_title": str(experience.get("title") or ""),
                }
            )
        )
    return resolved


def _target_index(
    section: OptimizedCVSection, experiences: list[dict[str, Any]]
) -> int | None:
    found = _EXPERIENCE_ID.match(section.target_id.strip().lower())
    if found and 1 <= int(found.group(1)) <= len(experiences):
        return int(found.group(1)) - 1

    head = _words(f"{section.original_excerpt} {section.rewritten_text[:200]}")
    candidates: list[tuple[int, int]] = []
    for index, experience in enumerate(experiences):
        title = _words(str(experience.get("title") or ""))
        company = _words(str(experience.get("company") or ""))
        if title.strip() and title in head:
            candidates.append(
                (index, 1 + int(bool(company.strip()) and company in head))
            )
    if not candidates:
        return None
    best = max(score for _, score in candidates)
    top = [index for index, score in candidates if score == best]
    return top[0] if len(top) == 1 else None


def _distinct_skill_names(primary_cv: dict[str, Any]) -> list[str]:
    """Los nombres de las habilidades del CV, una vez cada uno y en su orden."""
    names: dict[str, str] = {}
    for skill in _cv_sections(primary_cv).get("skills") or []:
        name = str(skill.get("name") or "") if isinstance(skill, dict) else str(skill)
        key = normalize_text(name)
        if key and key not in names:
            names[key] = name.strip()
    return list(names.values())


def ensure_declared_written(
    sections: list[OptimizedCVSection],
    declared: Sequence[str],
    primary_cv: dict[str, Any],
) -> list[OptimizedCVSection]:
    """Cada keyword declarada queda escrita en el texto nuevo, aunque la IA la omita.

    Las que ningún texto nombra se suman a la lista de habilidades: a la sección
    `skills` que devolvió la IA o, si no hubo, a una propia con las habilidades del CV.
    Nunca van a una experiencia: no hay un cargo ni un logro que las respalde.
    """
    written = "\n".join(section.rewritten_text for section in sections)
    pending = [keyword for keyword in declared if not _mentions(written, keyword)]
    if not pending:
        return sections

    result = list(sections)
    for index, section in enumerate(result):
        if section.section_name == "skills":
            result[index] = section.model_copy(
                update={"rewritten_text": _with_items(section.rewritten_text, pending)}
            )
            return result

    current = ", ".join(_distinct_skill_names(primary_cv))
    result.append(
        OptimizedCVSection(
            section_name="skills",
            original_excerpt=current,
            rewritten_text=_with_items(current, pending),
            added_keywords=[],
            rationale="Habilidades que declaraste saber y tu CV no menciona.",
        )
    )
    return result


def _with_items(text: str, items: Sequence[str]) -> str:
    return ", ".join([part for part in (text.strip().rstrip(",;"),) if part] + [*items])


def verify_sections(
    sections: list[OptimizedCVSection],
    matches: list[ATSKeywordMatch],
    cv_text: str,
    evidence: Sequence[str] = (),
    declared: Sequence[str] = (),
) -> list[OptimizedCVSection]:
    """Separa las keywords con respaldo en el CV de las que la IA agregó sin él.

    Usa el reporte ATS ya calculado (literal y semántico tienen evidencia en el CV;
    ausente no) y, para las ausentes, los textos del CV (`evidence`): una keyword que el
    CV dice con otras palabras tiene respaldo. Las que la persona declaró saber
    (`declared`) no son «sin respaldo»: se anotan aparte en cada sección que las
    escribe. No hace llamadas a la IA ni pide vectores.
    """
    status_by_keyword = {
        normalize_text(match.keyword): match.status for match in matches
    }
    missing = [match.keyword for match in matches if match.status == "missing"]
    declared_keys = {normalize_text(keyword) for keyword in declared}

    verified: list[OptimizedCVSection] = []
    backed = {keyword for keyword in missing if _supported_by_cv(keyword, evidence)}
    for section in sections:
        text = section.rewritten_text
        unverified = {
            normalize_text(keyword): keyword
            for keyword in missing
            if _mentions(text, keyword)
            and keyword not in backed
            and normalize_text(keyword) not in declared_keys
        }
        added: list[str] = []
        for keyword in section.added_keywords:
            key = normalize_text(keyword)
            if (
                key in unverified
                or key in declared_keys
                or not _mentions(text, keyword)
            ):
                # Ya marcada sin respaldo, declarada por la persona (se anota aparte)
                # o la IA la declaró pero no la escribió.
                continue
            status = status_by_keyword.get(key)
            backed_by_cv = _mentions(cv_text, keyword)
            if status == "missing" and keyword not in backed:
                unverified[key] = keyword
                continue
            if (
                status is None
                and not backed_by_cv
                and not _supported_by_cv(keyword, evidence)
            ):
                unverified[key] = keyword
                continue
            added.append(keyword)
        # Las que el texto nuevo escribe y el CV respalda cuentan aunque la IA no las
        # haya declarado.
        confirmed = [
            keyword
            for keyword in missing
            if keyword in backed and _mentions(text, keyword)
        ]
        stated = [
            keyword
            for keyword in declared
            if keyword not in backed and _mentions(text, keyword)
        ]
        verified.append(
            section.model_copy(
                update={
                    "added_keywords": added,
                    "unverified_keywords": list(unverified.values()),
                    "backed_keywords": confirmed,
                    "declared_keywords": stated,
                }
            )
        )
    return verified


def score_after_optimization(
    sections: list[OptimizedCVSection],
    matches: list[ATSKeywordMatch],
    requirements: list[ATSRequirement],
) -> int:
    """Puntaje ATS si se usan las secciones nuevas, contando solo lo verificado.

    Una keyword semántica que el texto nuevo nombra pasa a literal. Una ausente solo
    pasa si el CV la respalda con otras palabras (`backed_keywords`) o si la persona
    la declaró y el texto la escribe (`declared_keywords`); las demás siguen ausentes
    aunque el texto las mencione: nadie responde por ellas. Los requisitos (años,
    formación, idiomas) no cambian: reescribir texto no los cambia.
    """
    rewritten = "\n".join(section.rewritten_text for section in sections)
    backed = {
        normalize_text(keyword)
        for section in sections
        for keyword in (*section.backed_keywords, *section.declared_keywords)
    }
    updated = [
        match.model_copy(update={"status": "literal"})
        if (match.status == "semantic" and _mentions(rewritten, match.keyword))
        or (match.status == "missing" and normalize_text(match.keyword) in backed)
        else match
        for match in matches
    ]
    return compose_ats_score(updated, requirements)


async def optimize_cv_sections(
    primary_cv: dict[str, Any],
    job: dict[str, Any],
    matches: list[ATSKeywordMatch],
    user_tier: UserTier,
    gateway: AIGateway | None = None,
    declared: Sequence[str] = (),
) -> list[OptimizedCVSection]:
    missing_or_semantic = _low_coverage_keywords(matches)
    if not missing_or_semantic:
        return []

    ai_gateway = gateway or AIGateway()
    sections = await _rewrite_sections(
        ai_gateway, user_tier, _prompt(primary_cv, job, matches, declared)
    )
    sections = ensure_declared_written(sections, declared, primary_cv)
    cv_text = json.dumps(_cv_sections(primary_cv), ensure_ascii=False)
    verified = verify_sections(
        sections, matches, cv_text, evidence_texts(primary_cv), declared
    )
    return attach_targets(verified, primary_cv)


async def _rewrite_sections(
    ai_gateway: AIGateway,
    user_tier: UserTier,
    prompt: str,
) -> list[OptimizedCVSection]:
    """Secciones reescritas por la IA del plan; un premium cae al plan gratis si falla.

    Que Claude no responda (sin saldo, caído) o devuelva un JSON roto no debe dejar a
    quien paga sin su CV optimizado: se prueba con DeepSeek, que ya optimiza el plan
    gratis, y la verificación contra el CV es la misma. Si ninguna sirve, se avisa con
    un error de IA no disponible en vez de dejar escapar la excepción del proveedor.
    """
    tiers: list[UserTier] = ["premium", "free"] if user_tier == "premium" else ["free"]
    last_error: Exception | None = None
    for tier in tiers:
        try:
            content = await ai_gateway.generate(
                "cv_optimization",
                tier,
                prompt,
                system=OPTIMIZER_SYSTEM,
                json_mode=True,
            )
            return _parse_response(content)
        except Exception as exc:
            logger.warning(
                "No se pudo optimizar el CV con el plan %s: %s: %s",
                tier,
                type(exc).__name__,
                str(exc)[:200],
            )
            last_error = exc
    raise ProviderUnavailableError(
        "cv_optimization", "Ningún plan de IA devolvió secciones utilizables."
    ) from last_error
