"""Componente de idiomas del MatchScore: nombre y nivel dentro del texto del puesto.

La IA devuelve cada idioma pedido como un único texto («Inglés intermedio (B1/B2)») y
el perfil guarda el nombre y el nivel por separado («Inglés», «professional»). Medido en
producción el 2026-10-14: comparar el texto entero contra el nombre daba 0 aunque la
persona tuviera el idioma.
"""

from typing import Any

import pytest

from app.services.match_engine import compute_match_score
from app.services.match_engine.s_languages import (
    _LEVEL_WORDS,
    LANGUAGE_LEVEL,
    compute_languages_score,
)
from tests.fakes import FakeSupabase


def _score(required: list[Any], *profile: tuple[str, str | None]) -> float:
    languages = [{"name": name, "proficiency": level} for name, level in profile]
    return compute_languages_score(languages, {"required_languages": required})


# --- el caso medido en producción -------------------------------------------------


def test_the_level_and_name_are_read_from_the_text_the_job_asks_for() -> None:
    assert _score(["Inglés intermedio (B1/B2)"], ("Inglés", "professional")) == 1.0


def test_a_lower_level_than_asked_scores_less_but_not_zero() -> None:
    score = _score(["Inglés intermedio (B1/B2)"], ("Inglés", "basic"))

    assert score == 0.75


def test_a_profile_without_the_language_scores_zero() -> None:
    assert _score(["Inglés intermedio (B1/B2)"], ("Español", "native")) == 0.0
    assert _score(["Inglés intermedio (B1/B2)"]) == 0.0


def test_an_english_requirement_matches_a_spanish_profile_name() -> None:
    assert _score(["English advanced"], ("Inglés", "advanced")) == 1.0
    assert _score(["English advanced"], ("Inglés", "intermediate")) == 0.75
    assert _score(["English advanced"], ("Inglés", "basic")) == 0.5


# --- nombre del idioma ------------------------------------------------------------


@pytest.mark.parametrize(
    ("asked", "profile"),
    [
        ("Inglés", "English"),
        ("English", "Inglés"),
        ("INGLES", "inglés"),
        ("ingles", "INGLÉS"),
        ("Español", "Spanish"),
        ("Spanish", "español"),
        ("Portugués", "Portuguese"),
        ("Portuguese", "PORTUGUES"),
        ("Francés", "French"),
        ("French", "frances"),
        ("Alemán", "German"),
        ("German", "Aleman"),
        ("Italiano", "Italian"),
        ("Italian", "italiano"),
    ],
)
def test_a_language_matches_across_spanish_english_accents_and_case(
    asked: str, profile: str
) -> None:
    assert _score([asked], (profile, "advanced")) == 1.0


def test_a_language_is_not_matched_to_a_different_one() -> None:
    assert _score(["Francés"], ("Inglés", "native")) == 0.0
    assert _score(["Portugués"], ("Español", "native")) == 0.0


def test_the_name_is_found_anywhere_in_the_text() -> None:
    assert _score(["Nivel intermedio de inglés"], ("Inglés", "advanced")) == 1.0
    assert _score(["Advanced English (C1)"], ("English", "advanced")) == 1.0


def test_a_profile_name_that_carries_a_level_still_matches() -> None:
    assert _score(["Inglés avanzado"], ("English (C1)", "advanced")) == 1.0


def test_a_language_outside_the_table_matches_by_its_own_name() -> None:
    assert _score(["Chino intermedio"], ("Chino", "intermediate")) == 1.0
    assert _score(["Japanese (B2)"], ("japanese", "basic")) == 0.75
    assert _score(["Chino intermedio"], ("Japonés", "native")) == 0.0


def test_a_text_that_names_two_languages_asks_for_both() -> None:
    assert _score(["Inglés y portugués"], ("Inglés", "advanced")) == 0.5
    assert (
        _score(
            ["Inglés y portugués"], ("Inglés", "advanced"), ("Portugués", "advanced")
        )
        == 1.0
    )


# --- nivel ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "level"),
    [
        ("Inglés básico", "basic"),
        ("English basic", "basic"),
        ("Inglés (A2)", "basic"),
        ("Inglés intermedio", "intermediate"),
        ("English intermediate", "intermediate"),
        ("Inglés B1", "intermediate"),
        ("Inglés B2", "intermediate"),
        ("Inglés avanzado", "advanced"),
        ("English advanced", "advanced"),
        ("Inglés C1", "advanced"),
        ("Inglés nativo", "native"),
        ("English native", "native"),
        ("Inglés C2", "native"),
        ("Inglés bilingüe", "bilingual"),
        ("English bilingual", "bilingual"),
    ],
)
def test_the_level_the_text_names_is_what_the_job_asks_for(
    text: str, level: str
) -> None:
    """Una persona justo en el nivel pedido lo cumple; un escalón menos resta 0,25."""
    asked = LANGUAGE_LEVEL[level]

    assert _score([text], ("Inglés", level)) == 1.0
    one_below = next((k for k, v in LANGUAGE_LEVEL.items() if v == asked - 1), None)
    if one_below is not None:
        assert _score([text], ("Inglés", one_below)) == 0.75


def test_a_text_without_a_level_asks_for_intermediate() -> None:
    assert _score(["English"], ("Inglés", "intermediate")) == 1.0
    assert _score(["English"], ("Inglés", "basic")) == 0.75
    assert _score(["English"], ("Inglés", "advanced")) == 1.0


def test_a_range_asks_for_its_lowest_level() -> None:
    assert _score(["Inglés B2/C1"], ("Inglés", "intermediate")) == 1.0
    assert _score(["Inglés intermedio/avanzado"], ("Inglés", "intermediate")) == 1.0


def test_every_level_word_points_to_a_known_level() -> None:
    assert set(_LEVEL_WORDS.values()) <= set(LANGUAGE_LEVEL)


# --- formas que ya existían -------------------------------------------------------


def test_a_requirement_given_as_a_dict_keeps_working() -> None:
    required = [{"name": "english", "level": "advanced"}]

    assert _score(required, ("english", "advanced")) == 1.0
    assert _score(required, ("english", "basic")) == 0.5


def test_the_explicit_level_of_a_dict_wins_over_the_name() -> None:
    required = [{"name": "Inglés avanzado", "level": "basic"}]

    assert _score(required, ("Inglés", "basic")) == 1.0


def test_a_dict_without_level_reads_it_from_the_name() -> None:
    required = [{"name": "Inglés avanzado", "level": None}]

    assert _score(required, ("Inglés", "basic")) == 0.5


def test_the_languages_can_come_inside_a_dict() -> None:
    job = {"required_languages": {"languages": ["Inglés avanzado"]}}
    languages = [{"name": "English", "proficiency": "advanced"}]

    assert compute_languages_score(languages, job) == 1.0


def test_the_proficiency_or_the_level_key_of_the_profile_is_used() -> None:
    job = {"required_languages": ["Inglés avanzado"]}

    assert (
        compute_languages_score([{"name": "Inglés", "level": "advanced"}], job) == 1.0
    )


def test_a_job_that_asks_for_no_language_keeps_the_neutral_score() -> None:
    assert _score([], ("Inglés", "advanced")) == 0.85
    assert compute_languages_score([], {"required_languages": None}) == 0.85
    assert compute_languages_score([], {}) == 0.85


def test_an_unreadable_level_in_the_profile_counts_as_intermediate() -> None:
    assert _score(["Inglés intermedio"], ("Inglés", "unknown")) == 1.0
    assert _score(["Inglés avanzado"], ("Inglés", None)) == 0.75


def test_the_scores_of_several_languages_are_averaged() -> None:
    score = _score(
        ["Inglés intermedio", "Portugués avanzado"],
        ("English", "professional"),
        ("Portugués", "intermediate"),
    )

    assert score == pytest.approx((1.0 + 0.75) / 2)


def test_the_same_language_twice_in_the_profile_keeps_the_best_level() -> None:
    languages = [("Inglés", "basic"), ("English", "advanced")]

    assert _score(["Inglés avanzado"], *languages) == 1.0
    assert _score(["Inglés avanzado"], *reversed(languages)) == 1.0


# --- de punta a punta -------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_match_score_counts_a_language_the_job_wrote_with_its_level() -> None:
    db = FakeSupabase()
    db.tables["master_profiles"] = [
        {
            "id": "p1",
            "user_id": "u1",
            "target_seniority": "senior",
            "work_modality": "onsite",
            "target_industry": [],
            "inferred_soft_skills": [],
        }
    ]
    db.tables["languages"] = [
        {
            "id": "l1",
            "profile_id": "p1",
            "name": "Inglés",
            "proficiency": "professional",
        }
    ]
    db.tables["job_descriptions"] = [
        {
            "id": "j1",
            "user_id": "u1",
            "job_title": "Backend Engineer",
            "raw_text": None,
            "required_seniority": "senior",
            "required_modality": "onsite",
            "industry": "software",
            "tech_stack": [],
            "required_skills": [],
            "soft_skills": [],
            "required_education": None,
            "required_languages": ["Inglés intermedio (B1/B2)"],
            "embedding": None,
        }
    ]

    result = await compute_match_score("p1", "j1", db)

    assert result.score_breakdown["sub_scores"]["languages"] == 1.0
