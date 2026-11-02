from collections.abc import Sequence
from typing import Protocol


class _KeywordStatus(Protocol):
    @property
    def status(self) -> str: ...


class _Requirement(Protocol):
    @property
    def key(self) -> str: ...

    @property
    def ratio(self) -> float: ...


# Peso de cada parte del puntaje (Decisión 42). Es una propuesta del cambio, no un dato
# medido: las skills pesan lo que más porque son lo que el reclutador busca en el texto.
# Lo que el aviso no pide no entra: los pesos se reparten entre lo que sí se evalúa.
WEIGHT_SKILLS = 60
WEIGHT_EXPERIENCE = 20
WEIGHT_EDUCATION = 10
WEIGHT_LANGUAGES = 10  # se reparte entre los idiomas que pide el aviso


# Lo que suma una palabra clave según cómo aparece en el CV, y cuánto pesa si el aviso
# la presenta como deseable («nice to have», «se valora») frente a una obligatoria.
LITERAL_POINTS = 1.0
SEMANTIC_POINTS = 0.5
NICE_TO_HAVE_WEIGHT = 0.5


def _weight(match: object) -> float:
    return (
        NICE_TO_HAVE_WEIGHT if getattr(match, "priority", "required") == "nice" else 1.0
    )


def keyword_coverage(matches: Sequence[_KeywordStatus]) -> float:
    """Cuánto del puesto nombra el CV (0 a 1).

    Literal vale 1 y semántica, la mitad. Una palabra que el aviso presenta como
    deseable pesa la mitad que una obligatoria, tanto si la tiene como si le falta.
    """
    if not matches:
        return 1.0
    points = {"literal": LITERAL_POINTS, "semantic": SEMANTIC_POINTS}
    total = sum(_weight(match) for match in matches)
    earned = sum(_weight(match) * points.get(match.status, 0.0) for match in matches)
    return earned / total


def compose_ats_score(
    matches: Sequence[_KeywordStatus],
    requirements: Sequence[_Requirement] = (),
) -> int:
    """Puntaje 0-100: skills, años, formación e idiomas, cada uno por lo que cubre.

    Lo que supera lo pedido vale 1, igual que cumplirlo: no sube el puntaje. El formato
    del archivo no entra: se muestra aparte como lectura del CV (Decisión 42).
    """
    language_keys = [
        item.key for item in requirements if item.key.startswith("language:")
    ]
    parts: list[tuple[float, float]] = []
    if matches:
        parts.append((WEIGHT_SKILLS, keyword_coverage(matches)))
    for item in requirements:
        if item.key == "experience":
            parts.append((WEIGHT_EXPERIENCE, item.ratio))
        elif item.key == "education":
            parts.append((WEIGHT_EDUCATION, item.ratio))
        elif item.key in language_keys:
            parts.append((WEIGHT_LANGUAGES / len(language_keys), item.ratio))

    total = sum(weight for weight, _ in parts)
    if total == 0:
        return 100
    return round(100 * sum(weight * ratio for weight, ratio in parts) / total)


def compute_ats_score(
    matches: Sequence[_KeywordStatus],
    requirements: Sequence[_Requirement] = (),
) -> int:
    return compose_ats_score(matches, requirements)
