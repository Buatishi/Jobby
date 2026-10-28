"""El puntaje ATS se mueve cuando el CV mejora, aun con poca cobertura (Decisión 36).

Antes el formato restaba puntos fijos de la cobertura y el resultado no bajaba de 0:
un CV con 1 de 11 keywords (9 %) y dos problemas de formato (−20) daba −11, que se
mostraba como 0, y mejorar una cosa o la otra seguía dando 0.
"""

import pytest

from app.services.ats_analyzer.keyword_matcher import KeywordMatch
from app.services.ats_analyzer.scoring import score_keyword_coverage

KEYWORDS = 11


def _matches(literal: int, total: int = KEYWORDS) -> list[KeywordMatch]:
    return [
        KeywordMatch(f"skill-{index}", "literal" if index < literal else "missing")
        for index in range(total)
    ]


def test_a_low_coverage_with_format_problems_is_not_flattened_to_zero() -> None:
    # El reporte real que mostraba 0: 1 de 11 keywords y varias columnas + imágenes.
    # Cobertura 9,09 %; con el 20 % descontado queda 7,27 -> 7.
    assert score_keyword_coverage(_matches(literal=1), penalty=20) == 7


def test_adding_a_keyword_raises_the_score_even_under_the_old_floor() -> None:
    scores = [
        score_keyword_coverage(_matches(literal=count), penalty=20)
        for count in range(KEYWORDS + 1)
    ]

    # Con la resta fija, de 0 a 2 keywords daba 0 las tres veces.
    assert scores == sorted(set(scores))
    assert scores[0] == 0
    assert scores[1] > scores[0]
    assert scores[2] > scores[1]
    assert scores[-1] == 80


def test_fixing_a_format_problem_raises_the_score() -> None:
    matches = _matches(literal=1)

    assert score_keyword_coverage(matches, penalty=10) > score_keyword_coverage(
        matches, penalty=20
    )
    assert score_keyword_coverage(matches, penalty=0) > score_keyword_coverage(
        matches, penalty=10
    )


def test_a_complete_match_loses_exactly_the_published_points() -> None:
    # En lo más alto el descuento es el de siempre: 100 menos los puntos del problema.
    assert score_keyword_coverage(_matches(KEYWORDS), penalty=10) == 90
    assert score_keyword_coverage(_matches(KEYWORDS), penalty=25) == 75


def test_a_report_without_keywords_keeps_its_old_score() -> None:
    assert score_keyword_coverage([], penalty=0) == 100
    assert score_keyword_coverage([], penalty=25) == 75


def test_a_semantic_match_still_counts_half() -> None:
    matches = [
        KeywordMatch("a", "literal"),
        KeywordMatch("b", "semantic"),
        KeywordMatch("c", "missing"),
        KeywordMatch("d", "missing"),
    ]

    # (1 + 0,5) / 4 = 37,5 % de cobertura; sin formato redondea a 38.
    assert score_keyword_coverage(matches, penalty=0) == 38


@pytest.mark.parametrize("penalty", [0, 5, 10, 20, 35])
def test_each_extra_keyword_adds_points_for_every_published_penalty(
    penalty: int,
) -> None:
    scores = [
        score_keyword_coverage(_matches(literal=count), penalty=penalty)
        for count in range(KEYWORDS + 1)
    ]

    pairs = zip(scores, scores[1:], strict=False)
    assert all(later > earlier for earlier, later in pairs)


@pytest.mark.parametrize("penalty", [100, 140])
def test_a_penalty_of_a_hundred_or_more_leaves_zero_never_a_negative(
    penalty: int,
) -> None:
    assert score_keyword_coverage(_matches(KEYWORDS), penalty=penalty) == 0
    assert score_keyword_coverage([], penalty=penalty) == 0
