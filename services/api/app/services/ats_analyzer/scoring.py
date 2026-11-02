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

# Del total de 100, el formato del archivo vale FORMAT_POINTS y el contenido (las cuatro
# partes de arriba, en la proporción 60/20/10/10) los CONTENT_POINTS restantes: con todo
# pedido, 54/18/9/9 y 10. El formato es una estimación propia del riesgo de que un ATS
# lea mal el archivo (columnas, imágenes, tablas), una convención de Jobby y no el
# puntaje de ningún ATS real: la investigación del 2026-10-31 no encontró ninguno que
# publique puntos por formato (Decisión 42). Siempre vale 10, pida lo que pida el aviso.
CONTENT_POINTS = 90
FORMAT_POINTS = 10


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
    format_points: int | None = None,
) -> int:
    """Puntaje 0-100: skills, años, formación e idiomas, cada uno por lo que cubre, y el
    formato del archivo.

    Lo que supera lo pedido vale 1, igual que cumplirlo: no sube el puntaje. El
    contenido aporta CONTENT_POINTS por lo que cubre y el formato, `format_points` (0 a
    FORMAT_POINTS). Sin `format_points` (el formato no se evaluó: un CV leído antes del
    chequeo) el formato no entra, ni suma ni resta, y el contenido vale los 100.
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
    # Un aviso que no pide nada medible se da por cubierto, como antes.
    content = 1.0 if total == 0 else sum(w * r for w, r in parts) / total
    if format_points is None:
        return round(100 * content)
    return round(CONTENT_POINTS * content + max(0, min(FORMAT_POINTS, format_points)))


def compute_ats_score(
    matches: Sequence[_KeywordStatus],
    requirements: Sequence[_Requirement] = (),
    format_points: int | None = None,
) -> int:
    return compose_ats_score(matches, requirements, format_points)
