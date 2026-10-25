from collections.abc import Sequence
from typing import Protocol

from app.services.ats_analyzer.format_checker import FormatIssue


class _KeywordStatus(Protocol):
    @property
    def status(self) -> str: ...


def compute_ats_score(
    matches: Sequence[_KeywordStatus],
    format_issues: list[FormatIssue],
) -> int:
    return score_keyword_coverage(
        matches,
        sum(issue.penalty for issue in format_issues),
    )


def score_keyword_coverage(matches: Sequence[_KeywordStatus], penalty: int) -> int:
    """Cobertura de keywords (0-100) con el formato descontado en proporción.

    Cada punto de `penalty` quita ese porcentaje de lo que el CV cubre: con cobertura
    completa el descuento son exactamente los puntos publicados (100 → 90 con una
    tabla), y con poca cobertura es proporcionalmente menor. Restar los puntos fijos
    dejaba en 0 a todo CV con menos de `penalty` % de cobertura, y ahí ni sumar una
    keyword ni arreglar el formato movía el número (Decisión 36).
    """
    if matches:
        literal_hits = sum(1 for match in matches if match.status == "literal")
        semantic_hits = sum(1 for match in matches if match.status == "semantic")
        coverage = ((literal_hits * 1.0 + semantic_hits * 0.5) / len(matches)) * 100
    else:
        coverage = 100.0
    return round(coverage * max(0, 100 - penalty) / 100)
