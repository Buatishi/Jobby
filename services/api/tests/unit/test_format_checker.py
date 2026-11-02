"""El chequeo de formato del ATS: cuánto resta cada aviso y cuándo no se evaluó."""

from typing import Any

import pytest

from app.services.ats_analyzer.format_checker import (
    PENALTY_IMAGES,
    PENALTY_MULTI_COLUMN,
    PENALTY_TABLES,
    check_cv_format,
    format_points,
    format_was_evaluated,
)
from app.services.ats_analyzer.scoring import FORMAT_POINTS


def _cv(flags: Any) -> dict[str, Any]:
    return {"parsed_data": {"skills": [], "format_flags": flags}}


def _penalties(flags: Any) -> dict[str, int]:
    return {issue.code: issue.penalty for issue in check_cv_format(_cv(flags))}


def test_each_problem_costs_its_penalty_out_of_the_format_points() -> None:
    flags = {
        "has_tables": True,
        "multi_column": True,
        "has_images": True,
        "headers": ["Perfil académico"],
    }

    # Columnas −4, imágenes −3 y tablas −3 (Decisión 42): una convención de Jobby. Los
    # títulos poco habituales se avisan pero no restan.
    assert _penalties(flags) == {
        "TABLES": 3,
        "MULTI_COLUMN": 4,
        "IMAGES": 3,
        "NON_STANDARD_HEADERS": 0,
    }


def test_the_three_penalties_take_all_the_format_points() -> None:
    assert PENALTY_MULTI_COLUMN + PENALTY_IMAGES + PENALTY_TABLES == FORMAT_POINTS


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        ({}, 10),
        ({"multi_column": True}, 6),
        ({"has_images": True}, 7),
        ({"has_tables": True}, 7),
        # Los dos avisos del archivo medido el 2026-11-02: 3 de 10.
        ({"multi_column": True, "has_images": True}, 3),
        ({"multi_column": True, "has_images": True, "has_tables": True}, 0),
        # Los títulos poco habituales no restan.
        ({"headers": ["Perfil académico"]}, 10),
    ],
)
def test_the_format_points_are_ten_minus_what_each_notice_costs(
    flags: dict[str, Any], expected: int
) -> None:
    assert format_points(check_cv_format(_cv(flags))) == expected


def test_the_format_points_never_go_below_zero() -> None:
    class _Heavy:
        penalty = 25

    assert format_points([_Heavy()]) == 0


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


def test_a_cv_with_no_usual_title_is_noticed_once_without_points() -> None:
    flags = {"headers": ["Perfil académico", "Contacto", "Trayectoria"]}

    assert _penalties(flags) == {"NON_STANDARD_HEADERS": 0}


def test_unusual_titles_among_usual_ones_cost_nothing() -> None:
    flags = {"headers": ["Experiencia", "Perfil académico", "Contacto"]}

    assert _penalties(flags) == {}


@pytest.mark.parametrize(
    "header",
    [
        "Experiencia profesional",
        "EXPERIENCIA PROFESIONAL",
        "Habilidades y competencias",
        "HABILIDADES Y COMPETENCIAS",
        "Educación y formación",
        "Work Experience",
        "Technical Skills",
        "Skills & Tools",
        "Idiomas:",
    ],
)
def test_a_title_with_a_usual_word_is_usual(header: str) -> None:
    assert _penalties({"headers": [header]}) == {}


def test_a_word_inside_another_word_is_not_a_usual_title() -> None:
    # «Skillset» y «Pre-educación» no son «skills» ni «educacion».
    assert _penalties({"headers": ["Skillset", "Supereducacion"]}) == {
        "NON_STANDARD_HEADERS": 0
    }


def test_company_names_read_as_titles_do_not_cost_anything() -> None:
    # Caso medido en producción: el lector del PDF devolvió tres nombres de empresa en
    # mayúsculas junto a los títulos reales. Los nombres de acá son inventados.
    flags = {
        "headers": [
            "HABILIDADES Y COMPETENCIAS",
            "EXPERIENCIA PROFESIONAL",
            "ACME SRL",
            "PLANOS CAD",
            "TIENDA DEMO",
            "EDUCACIÓN",
        ]
    }

    assert _penalties(flags) == {}


def test_a_cv_with_no_titles_read_costs_nothing_for_them() -> None:
    assert _penalties({"headers": []}) == {}
    assert _penalties({}) == {}


def test_a_cv_without_parsed_data_is_noticed_but_not_scored() -> None:
    [issue] = check_cv_format({"parsed_data": None})

    # Sin datos el formato no se evaluó: no cuenta, así que el aviso no resta.
    assert (issue.code, issue.penalty) == ("NO_PARSED_DATA", 0)
    assert format_was_evaluated({"parsed_data": None}) is False


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
