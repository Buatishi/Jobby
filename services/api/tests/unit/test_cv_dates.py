"""Fechas del CV: el formato que guarda el lector y «actualidad» (Decisión 41).

Las fechas son de ejemplo. El lector no debe fallar con ningún valor: lo que no entiende
como fecha lo deja como texto o lo descarta.
"""

from typing import Any

import pytest

from app.services.cv_parser.dates import (
    is_present_marker,
    normalize_date,
    read_period,
)

# --- una fecha suelta ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("written", "stored"),
    [
        # mes y año en los dos idiomas, con o sin «de», abreviados o completos
        ("Julio 2026", "2026-07"),
        ("julio de 2026", "2026-07"),
        ("JULIO 2026", "2026-07"),
        ("Jul 2026", "2026-07"),
        ("Jul. 2026", "2026-07"),
        ("July 2026", "2026-07"),
        ("Setiembre 2019", "2019-09"),
        ("Sept. 2019", "2019-09"),
        ("Septiembre de 2019", "2019-09"),
        ("Sep 2019", "2019-09"),
        ("Enero 2020", "2020-01"),
        ("Dic 2021", "2021-12"),
        ("Dec 2021", "2021-12"),
        ("Mar 2022", "2022-03"),
        ("Mayo 2018", "2018-05"),
        ("Aug, 2018", "2018-08"),
        ("15 de julio de 2026", "2026-07"),
        ("3 March 2020", "2020-03"),
        # número de mes y año
        ("03/2021", "2021-03"),
        ("3/2021", "2021-03"),
        ("03-2021", "2021-03"),
        ("03.2021", "2021-03"),
        ("2021/03", "2021-03"),
        # ya viene en ISO: se respeta lo que trae
        ("2021-03", "2021-03"),
        ("2021-03-15", "2021-03-15"),
        # solo el año
        ("2019", "2019"),
        ("  2019 ", "2019"),
    ],
)
def test_an_unambiguous_date_is_stored_as_year_and_month(
    written: str, stored: str
) -> None:
    assert normalize_date(written) == stored


@pytest.mark.parametrize(
    "written",
    [
        "Verano 2020",  # no es un mes
        "Q1 2021",
        "Hace dos años",
        "15/03/2021",  # día/mes o mes/día: no se adivina
        "13/2021",  # mes inexistente
        "2021-13",
        "Mayo",  # sin año
        "1850",  # fuera de rango
        "2150",
    ],
)
def test_what_is_not_an_unambiguous_date_is_kept_as_the_cv_wrote_it(
    written: str,
) -> None:
    assert normalize_date(written) == written


@pytest.mark.parametrize(
    ("value", "stored"),
    [
        (None, ""),
        ("", ""),
        ("   ", ""),
        (True, ""),
        (False, ""),
        (2021, "2021"),
        (2021.0, "2021"),
        (7, ""),  # un número chico no es un año
        (1.5, ""),
        (10**400, ""),
        (-(10**400), ""),
        (1e308, ""),
        (float("inf"), ""),
        (float("nan"), ""),
        ({"year": 10**400}, ""),
        ({"year": 2026, "month": 10**400}, "2026"),
        ({"year": 2026, "month": float("inf")}, "2026"),
        ([], ""),
        (["2021"], ""),
        ({}, ""),
        ({"year": 2020}, "2020"),
        ({"year": "2020", "month": "July"}, "2020-07"),
        ({"year": 2026, "month": 7}, "2026-07"),
        ({"year": 2026, "month": 13}, "2026"),
        ({"month": "July"}, ""),
        ({"text": "Julio 2026"}, "2026-07"),
        ({"value": {"nested": "x"}}, ""),
        ({"year": {"x": 1}}, ""),
        (object(), ""),
        ("x" * 500, ""),  # un párrafo no es una fecha
    ],
)
def test_a_value_that_is_not_text_never_fails_and_leaves_nothing_or_a_year(
    value: Any, stored: str
) -> None:
    assert normalize_date(value) == stored


# --- «actualidad» ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "written",
    [
        "Presente",
        "presente",
        "PRESENTE",
        "Actual",
        "Actualidad",
        "actualmente",
        "Hoy",
        "A la fecha",
        "Hasta la fecha",
        "Hasta la actualidad",
        "Al presente",
        "Present",
        "To date",
        "Current",
        "Currently",
        "Now",
        "Ongoing",
        "En curso",
        "Cursando",
        "In progress",
        "Presente (3 años)",
    ],
)
def test_the_words_that_mean_it_is_still_going_are_recognised(written: str) -> None:
    assert is_present_marker(written) is True


@pytest.mark.parametrize(
    "written",
    [
        "",
        "Marzo 2025",
        "2024",
        "Actualizado 2020",
        "Fechado 2019",
        "Currency exchange",
        "Date: 2020",
        "Ahora no",
    ],
)
def test_a_date_or_an_unrelated_word_is_not_a_present_marker(written: str) -> None:
    assert is_present_marker(written) is False


def test_a_non_text_value_is_not_a_present_marker() -> None:
    assert is_present_marker(None) is False
    assert is_present_marker(3) is False
    assert is_present_marker({"text": "Presente"}) is False


# --- un período -----------------------------------------------------------------------

START = ("started_at", "start_date", "from")
END = ("ended_at", "end_date", "to")
FLAG = ("is_current", "current")


def _period(item: dict[str, Any]) -> tuple[str, str, bool]:
    return read_period(item, START, END, FLAG)


def test_a_closed_period_keeps_both_dates() -> None:
    assert _period({"started_at": "Julio 2024", "ended_at": "Marzo 2025"}) == (
        "2024-07",
        "2025-03",
        False,
    )


def test_a_period_without_dates_is_empty_and_not_current() -> None:
    assert _period({}) == ("", "", False)
    assert _period({"started_at": None, "ended_at": None, "is_current": None}) == (
        "",
        "",
        False,
    )


@pytest.mark.parametrize("marker", ["Presente", "Actual", "Actualidad", "Present"])
def test_an_end_date_that_is_a_present_marker_means_current_and_leaves_no_end(
    marker: str,
) -> None:
    assert _period({"started_at": "Julio 2026", "ended_at": marker}) == (
        "2026-07",
        "",
        True,
    )


def test_the_flag_alone_means_current() -> None:
    assert _period({"started_at": "2026", "is_current": True}) == ("2026", "", True)


@pytest.mark.parametrize("flag", [True, "true", "True", "yes", "sí", "si", 1, "1"])
def test_the_ways_the_ai_writes_true(flag: Any) -> None:
    assert _period({"is_current": flag})[2] is True


@pytest.mark.parametrize(
    "flag", [False, "false", "no", 0, "0", None, "", "quizás", 2, [], {}, ["true"]]
)
def test_anything_else_is_not_current(flag: Any) -> None:
    assert _period({"is_current": flag})[2] is False


def test_a_real_end_date_wins_over_a_flag_that_says_current() -> None:
    """La fecha sale del CV; la bandera es una inferencia de la IA."""
    assert _period({"ended_at": "Marzo 2025", "is_current": True}) == (
        "",
        "2025-03",
        False,
    )


def test_a_present_marker_wins_over_a_flag_that_says_not_current() -> None:
    assert _period({"ended_at": "Presente", "is_current": False})[2] is True


def test_the_usual_alternative_keys_are_read() -> None:
    assert _period({"start_date": "Mar 2020", "end_date": "Dic 2021"}) == (
        "2020-03",
        "2021-12",
        False,
    )
    assert _period({"from": "2020", "to": "Present", "current": "true"}) == (
        "2020",
        "",
        True,
    )


def test_the_first_key_with_a_value_is_used() -> None:
    assert _period({"started_at": "", "start_date": "2020"})[0] == "2020"
    assert _period({"started_at": None, "from": "2019"})[0] == "2019"


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        ("Julio 2026 - Presente", ("2026-07", "", True)),
        ("Julio 2026 – Presente", ("2026-07", "", True)),
        ("Julio 2026 — Actualidad", ("2026-07", "", True)),
        ("Jul 2024 - Mar 2025", ("2024-07", "2025-03", False)),
        ("03/2020 - 05/2021", ("2020-03", "2021-05", False)),
        ("2019 - 2021", ("2019", "2021", False)),
        ("2019-2021", ("2019", "2021", False)),
        ("2019 – 2021", ("2019", "2021", False)),
        ("2019 a 2021", ("2019", "2021", False)),
        ("Marzo 2020 hasta Presente", ("2020-03", "", True)),
        ("2020 to Present", ("2020", "", True)),
    ],
)
def test_a_range_written_in_the_start_field_is_split_when_there_is_no_end(
    written: str, expected: tuple[str, str, bool]
) -> None:
    assert _period({"started_at": written}) == expected


def test_a_range_is_not_split_when_the_end_is_already_there() -> None:
    assert _period({"started_at": "2019 - 2021", "ended_at": "2022"}) == (
        "2019 - 2021",
        "2022",
        False,
    )


def test_a_single_iso_date_is_not_mistaken_for_a_range() -> None:
    assert _period({"started_at": "2021-03"}) == ("2021-03", "", False)
    assert _period({"started_at": "2021-03-15"}) == ("2021-03-15", "", False)


def test_garbage_in_any_field_does_not_raise() -> None:
    hostile: dict[str, Any] = {
        "started_at": {"x": [1, 2, {"y": None}]},
        "ended_at": ["Presente"],
        "is_current": {"value": True},
    }

    assert _period(hostile) == ("", "", False)
