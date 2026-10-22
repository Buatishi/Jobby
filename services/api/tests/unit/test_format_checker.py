"""El chequeo de formato del ATS: qué resta cada problema y cuándo no se evaluó."""

from typing import Any

import pytest

from app.services.ats_analyzer.format_checker import (
    check_cv_format,
    format_was_evaluated,
)


def _cv(flags: Any) -> dict[str, Any]:
    return {"parsed_data": {"skills": [], "format_flags": flags}}


def _penalties(flags: Any) -> dict[str, int]:
    return {issue.code: issue.penalty for issue in check_cv_format(_cv(flags))}


def test_each_problem_costs_its_published_penalty() -> None:
    flags = {
        "has_tables": True,
        "multi_column": True,
        "has_images": True,
        "headers": ["Perfil académico"],
    }

    assert _penalties(flags) == {
        "TABLES": 10,
        "MULTI_COLUMN": 10,
        "IMAGES": 10,
        "NON_STANDARD_HEADERS": 5,
    }


def test_a_clean_cv_has_no_issues() -> None:
    flags = {
        "has_tables": False,
        "multi_column": False,
        "has_images": False,
        "headers": ["EXPERIENCIA", "EDUCACION", "HABILIDADES"],
    }

    assert check_cv_format(_cv(flags)) == []


@pytest.mark.parametrize(
    "header",
    [
        "Experiencia",
        "EXPERIENCIA",
        "Educación",
        "EDUCACIÓN",
        "habilidades:",
        "  Skills  ",
        "Idiomas",
        "Certificaciones",
        "Experience",
    ],
)
def test_the_usual_titles_match_whatever_the_case_accents_or_colon(header: str) -> None:
    assert _penalties({"headers": [header]}) == {}


def test_one_unusual_title_costs_the_penalty_once() -> None:
    flags = {"headers": ["Experiencia", "Perfil académico", "Contacto"]}

    assert _penalties(flags) == {"NON_STANDARD_HEADERS": 5}


def test_a_cv_without_parsed_data_keeps_its_penalty() -> None:
    [issue] = check_cv_format({"parsed_data": None})

    assert (issue.code, issue.penalty) == ("NO_PARSED_DATA", 20)


@pytest.mark.parametrize(
    ("primary_cv", "expected"),
    [
        # Leído después del cambio: las banderas están, aunque no haya problemas.
        (_cv({"has_tables": False, "headers": []}), True),
        (_cv({}), True),
        # Leído antes del cambio, o cuando el análisis del PDF falló: no se sabe.
        ({"parsed_data": {"skills": []}}, False),
        (_cv(None), False),
        (_cv("sí"), False),
        ({"parsed_data": None}, False),
        ({}, False),
    ],
)
def test_a_cv_without_format_flags_was_not_evaluated(
    primary_cv: dict[str, Any], expected: bool
) -> None:
    assert format_was_evaluated(primary_cv) is expected
