"""El formato del archivo vale 10 de los 100 puntos del reporte ATS (Decisión 42).

El contenido (palabras clave, años, formación e idiomas) aporta los otros 90, en la
proporción de siempre: con todo pedido, 54/18/9/9. Los 10 del formato son una
convención de Jobby, no el puntaje de ningún ATS real.
"""

from dataclasses import dataclass

import pytest

from app.models.ats import ATSKeywordMatch, OptimizedCVSection
from app.services.ats_analyzer.cv_optimizer import score_after_optimization
from app.services.ats_analyzer.scoring import (
    CONTENT_POINTS,
    FORMAT_POINTS,
    WEIGHT_EDUCATION,
    WEIGHT_EXPERIENCE,
    WEIGHT_LANGUAGES,
    WEIGHT_SKILLS,
    compose_ats_score,
    compute_ats_score,
)


@dataclass
class _Requirement:
    key: str
    ratio: float


def _matches(literal: int, missing: int) -> list[ATSKeywordMatch]:
    return [
        ATSKeywordMatch(keyword=f"Skill{n}", status="literal", matched_text="x")
        for n in range(literal)
    ] + [ATSKeywordMatch(keyword=f"Falta{n}", status="missing") for n in range(missing)]


FULL_POSTING = [
    _Requirement("experience", 1.0),
    _Requirement("education", 1.0),
    _Requirement("language:english", 1.0),
]


def test_the_points_add_up_to_a_hundred() -> None:
    assert CONTENT_POINTS + FORMAT_POINTS == 100
    assert FORMAT_POINTS == 10
    # Las cuatro partes de contenido siguen en la proporción 60/20/10/10.
    assert (WEIGHT_SKILLS, WEIGHT_EXPERIENCE, WEIGHT_EDUCATION, WEIGHT_LANGUAGES) == (
        60,
        20,
        10,
        10,
    )


def _only(part: str) -> int:
    """El puntaje, con el formato en 0, de un CV que cumple solo esa parte del aviso."""
    matches = _matches(1, 0) if part == "skills" else _matches(0, 1)
    requirements = [
        _Requirement("experience", 1.0 if part == "experience" else 0.0),
        _Requirement("education", 1.0 if part == "education" else 0.0),
        _Requirement("language:english", 1.0 if part == "language" else 0.0),
    ]
    return compose_ats_score(matches, requirements, 0)


def test_with_everything_asked_the_parts_are_worth_54_18_9_and_9() -> None:
    parts = ("skills", "experience", "education", "language")

    assert {part: _only(part) for part in parts} == {
        "skills": 54,
        "experience": 18,
        "education": 9,
        "language": 9,
    }


def test_a_perfect_cv_with_a_clean_file_is_a_hundred() -> None:
    assert compose_ats_score(_matches(3, 0), FULL_POSTING, 10) == 100


def test_the_format_is_ten_points_whatever_the_posting_asks() -> None:
    perfect_keywords = _matches(3, 0)

    # Un aviso que pide solo palabras clave y otro que pide todo: el formato pesa lo
    # mismo, 10 puntos, y no más porque haya menos partes entre las que repartir.
    for requirements in ([], FULL_POSTING):
        clean = compose_ats_score(perfect_keywords, requirements, 10)
        without = compose_ats_score(perfect_keywords, requirements, 0)
        assert clean - without == 10
        assert without == 90


def test_the_format_points_move_the_score_one_for_one() -> None:
    matches = _matches(1, 1)  # la mitad del contenido: 45 de los 90

    assert [compose_ats_score(matches, [], points) for points in (0, 3, 7, 10)] == [
        45,
        48,
        52,
        55,
    ]


def test_without_format_points_the_content_is_worth_the_whole_hundred() -> None:
    """Formato no evaluado: ni suma ni resta (Decisión 42)."""
    matches = _matches(1, 1)

    assert compose_ats_score(matches, []) == 50
    assert compose_ats_score(matches, [], None) == 50
    assert compute_ats_score(matches, [], None) == 50


def test_the_format_points_are_kept_between_zero_and_ten() -> None:
    matches = _matches(1, 1)

    assert compose_ats_score(matches, [], 25) == compose_ats_score(matches, [], 10)
    assert compose_ats_score(matches, [], -4) == compose_ats_score(matches, [], 0)


def test_a_posting_that_asks_nothing_measurable_counts_as_covered() -> None:
    assert compose_ats_score([], [], 10) == 100
    assert compose_ats_score([], [], 3) == 93
    assert compose_ats_score([], [], None) == 100


def test_the_file_measured_on_2026_11_02_loses_seven_points_to_the_download() -> None:
    """Imagen de 207×315 pt y dos columnas: 3 de 10; el descargable da 10 de 10."""
    matches = _matches(1, 1)

    uploaded_file = compose_ats_score(matches, [], 3)
    downloadable = compose_ats_score(matches, [], FORMAT_POINTS)

    assert downloadable - uploaded_file == 7


# --- el «antes → después» del optimizador --------------------------------------------


def _skills(text: str) -> OptimizedCVSection:
    return OptimizedCVSection(
        section_name="skills",
        original_excerpt="Python",
        rewritten_text=text,
        added_keywords=[],
        rationale="Cubre el puesto.",
    )


def test_the_score_after_counts_the_format_of_the_downloadable_cv() -> None:
    matches = _matches(1, 1)
    sections = [_skills("Python")]

    before = compose_ats_score(matches, [], 3)  # el archivo subido: 3 de 10
    after = score_after_optimization(sections, matches, [], FORMAT_POINTS)

    assert (before, after) == (48, 55)


def test_the_score_after_without_format_points_leaves_the_format_out() -> None:
    matches = _matches(1, 1)

    assert score_after_optimization([_skills("Python")], matches, []) == 50


@pytest.mark.parametrize("format_points", [0, 3, 10])
def test_a_rewrite_that_adds_nothing_changes_only_the_format(
    format_points: int,
) -> None:
    matches = _matches(1, 1)
    sections = [_skills("Python, Falta0")]  # nadie la respalda: no cuenta

    content_only = score_after_optimization(sections, matches, [])
    with_format = score_after_optimization(sections, matches, [], format_points)

    assert content_only == 50
    assert with_format == round(45 + format_points)
