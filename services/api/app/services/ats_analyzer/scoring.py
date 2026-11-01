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


def keyword_coverage(matches: Sequence[_KeywordStatus]) -> float:
    """Cuánto del puesto nombra el CV (0 a 1): literal vale 1 y semántica, la mitad."""
    if not matches:
        return 1.0
    literal_hits = sum(1 for match in matches if match.status == "literal")
    semantic_hits = sum(1 for match in matches if match.status == "semantic")
    return (literal_hits * 1.0 + semantic_hits * 0.5) / len(matches)


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
