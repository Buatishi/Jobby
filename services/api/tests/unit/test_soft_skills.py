"""Las habilidades blandas se leen en los dos idiomas y salen del CV (Decisión 40).

Caso medido en producción: el puntaje de blandas dio 0 en los 8 puestos guardados aunque
el CV decía «trabajo colaborativo en equipo» y «resolución de incidencias». Tres causas:
el puesto escribe las suyas en texto libre y solo contaban las que se llamaban igual que
una de las diez del motor, en inglés; el detector no entendía acentos ni español; y las
experiencias que el motor leía eran las filas de `experiences`, vacías en esa cuenta,
mientras el CV tenía cuatro con texto. Los datos de acá son inventados.
"""

from typing import Any

import pytest

from app.services.match_engine import compute_match_score
from app.services.match_engine.common import experiences_with_text
from app.services.match_engine.s_relevance import build_profile_text
from app.services.match_engine.s_soft import (
    compute_soft_score,
    infer_soft_skills,
    required_soft_skills,
)
from tests.fakes import FakeSupabase


def _job(*soft: str) -> dict[str, Any]:
    return {"soft_skills": list(soft)}


def _experience(description: str = "", *achievements: str) -> dict[str, Any]:
    return {
        "title": "Analista",
        "description": description,
        "achievements": list(achievements),
    }


# --- lo que pide el puesto ---------------------------------------------------------


@pytest.mark.parametrize(
    ("phrase", "named"),
    [
        ("Teamwork", "collaboration"),
        ("Trabajo en equipo", "collaboration"),
        ("Collaboration", "collaboration"),
        ("Comunicación", "communication"),
        ("Clear written communication", "communication"),
        ("comunicación de resultados a negocio", "communication"),
        ("liderazgo", "leadership"),
        ("Leadership", "leadership"),
        ("Ganas de resolver problemas", "problem_solving"),
        ("Independent problem solving", "problem_solving"),
        ("problem_solving", "problem_solving"),
        ("Autonomía", "ownership"),
        ("Ownership", "ownership"),
        ("Flexibility", "adaptability"),
        ("Ganas de aprender", "adaptability"),
        ("Self-starter", "initiative"),
        ("Pensamiento analítico", "analytical"),
    ],
)
def test_a_phrase_of_the_job_names_the_skill_it_means(phrase: str, named: str) -> None:
    assert required_soft_skills(_job(phrase)) == [frozenset({named})]


def test_a_phrase_that_names_no_skill_is_not_required() -> None:
    job = _job("Curiosity", "Passion for innovation", "Mejora continua")

    assert required_soft_skills(job) == []


def test_a_phrase_that_names_two_skills_counts_once() -> None:
    [named] = required_soft_skills(_job("Autonomy to research and solve problems"))

    assert named == frozenset({"ownership", "problem_solving"})


def test_a_job_whose_soft_skills_are_not_recognized_is_neutral() -> None:
    # Antes daba 0 con cualquier CV: «Curiosity» no se llama como ninguna de las diez.
    result = compute_soft_score(
        {}, [_experience("Resolví incidentes")], _job("Curiosity")
    )

    assert result["score"] == 0.75


def test_a_job_with_no_soft_skills_is_neutral() -> None:
    assert compute_soft_score({}, [], _job())["score"] == 0.75
    assert compute_soft_score({}, [], {})["score"] == 0.75


def test_only_the_recognized_phrases_count_in_the_score() -> None:
    job = _job("Teamwork", "Curiosity", "Passion for innovation")

    met = compute_soft_score({}, [_experience("Trabajo colaborativo")], job)
    unmet = compute_soft_score({}, [_experience("Hice reportes")], job)

    assert met["score"] == 1.0
    assert unmet["score"] == 0.0


def test_a_phrase_with_two_skills_is_met_by_either() -> None:
    job = _job("Autonomy to research and solve problems")

    result = compute_soft_score({}, [_experience("Resolución de incidencias")], job)

    assert result["score"] > 0.9


# --- lo que dice el CV -------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "skill"),
    [
        ("Trabajo colaborativo en equipo", "collaboration"),
        ("Resolución de incidencias", "problem_solving"),
        ("Colaboré con el área de ventas", "collaboration"),
        ("Lideré un equipo de tres personas", "leadership"),
        ("Comunicación con clientes", "communication"),
        ("Analicé las ventas del trimestre", "analytical"),
        ("Fui responsable de la entrega", "ownership"),
        ("Solved incidents in production", "problem_solving"),
        ("Documented platform decisions", "communication"),
        ("Improved latency by 20%", "impact"),
    ],
)
def test_the_cv_shows_the_skill_in_either_language_with_or_without_accents(
    text: str, skill: str
) -> None:
    assert skill in infer_soft_skills([_experience(text)])


def test_the_achievements_count_as_much_as_the_description() -> None:
    assert "collaboration" in infer_soft_skills(
        [_experience("", "Trabajo en equipo con soporte")]
    )


@pytest.mark.parametrize(
    ("text", "skill"),
    [
        ("Soporte en telecomunicaciones", "communication"),
        ("Cálculo del balance mensual", "initiative"),
        ("Pulled the repository", "leadership"),
    ],
)
def test_a_root_inside_another_word_is_not_a_signal(text: str, skill: str) -> None:
    assert skill not in infer_soft_skills([_experience(text)])


def test_what_the_cv_says_now_wins_over_a_stale_cache() -> None:
    profile = {"inferred_soft_skills": ["leadership"]}
    job = _job("Teamwork")

    result = compute_soft_score(profile, [_experience("Trabajo colaborativo")], job)

    assert result["detected"] == ["collaboration"]
    assert result["score"] == 1.0


def test_the_cache_is_used_when_the_cv_says_nothing() -> None:
    profile = {"inferred_soft_skills": ["collaboration"]}

    result = compute_soft_score(profile, [_experience("")], _job("Teamwork"))

    assert result["detected"] == ["collaboration"]
    assert result["score"] == 1.0


# --- de dónde salen las experiencias -----------------------------------------------


def _cv(*experiences: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "type": "cv",
        "is_primary": True,
        "parsed_data": {"experiences": list(experiences)},
        **extra,
    }


def test_the_profile_rows_win_when_one_has_text() -> None:
    rows = [_experience("Atendí clientes")]
    documents = [_cv(_experience("Otra cosa"))]

    assert experiences_with_text(rows, documents) == rows


def test_the_cv_experiences_are_used_when_the_rows_have_no_text() -> None:
    rows = [{"title": "Freelance", "description": "", "achievements": []}]
    from_cv = _experience("Trabajo colaborativo")

    assert experiences_with_text(rows, [_cv(from_cv)]) == [from_cv]


def test_the_cv_experiences_are_used_when_the_profile_has_no_rows() -> None:
    from_cv = _experience("", "Resolución de incidencias")

    assert experiences_with_text([], [_cv(from_cv)]) == [from_cv]


def test_only_the_primary_cv_counts() -> None:
    rows: list[dict[str, Any]] = []
    other = _cv(_experience("Trabajo colaborativo"), is_primary=False)
    linkedin = _cv(_experience("Trabajo colaborativo"), type="linkedin")

    assert experiences_with_text(rows, [other, linkedin]) == rows


@pytest.mark.parametrize(
    "parsed_data",
    [
        None,
        {},
        {"experiences": None},
        {"experiences": ["texto"]},
        {"experiences": [{}]},
    ],
)
def test_a_cv_without_usable_experiences_leaves_the_rows_as_they_are(
    parsed_data: Any,
) -> None:
    rows = [{"title": "Freelance", "description": None, "achievements": None}]
    document = {"type": "cv", "is_primary": True, "parsed_data": parsed_data}

    assert experiences_with_text(rows, [document]) == rows


def test_the_relevance_text_includes_what_the_cv_tells() -> None:
    profile: dict[str, Any] = {}
    rows = [{"title": "Freelance", "description": "", "achievements": []}]
    cv = _cv(_experience("Automaticé reportes con Python"))

    text = build_profile_text(profile, [], experiences_with_text(rows, [cv]))

    assert "automatice reportes con python" in text


# --- el match completo --------------------------------------------------------------


def _world(rows: list[dict[str, Any]], cv: list[dict[str, Any]]) -> FakeSupabase:
    db = FakeSupabase()
    db.tables["master_profiles"] = [
        {
            "id": "p1",
            "user_id": "u1",
            "target_seniority": "junior",
            "work_modality": "remote",
            "target_industry": [],
            "inferred_soft_skills": [],
        }
    ]
    db.tables["skills"] = [
        {
            "id": "s1",
            "profile_id": "p1",
            "name": "python",
            "category": "technical",
            "confirmed": True,
            "in_cv": True,
            "embedding": None,
        }
    ]
    db.tables["educations"] = []
    db.tables["languages"] = []
    db.tables["experiences"] = [{"id": "x1", "profile_id": "p1", **row} for row in rows]
    db.tables["uploaded_documents"] = [
        {"id": "d1", "user_id": "u1", "profile_id": "p1", **document} for document in cv
    ]
    db.tables["job_descriptions"] = [
        {
            "id": "j1",
            "user_id": "u1",
            "job_title": "Backend",
            "raw_text": None,
            "required_seniority": "junior",
            "required_modality": "remote",
            "industry": "software",
            "tech_stack": ["python"],
            "required_skills": ["python"],
            "soft_skills": ["Teamwork", "Resolución de problemas"],
            "required_education": None,
            "required_languages": [],
            "embedding": None,
        }
    ]
    return db


@pytest.mark.asyncio
async def test_the_match_reads_the_cv_when_the_profile_rows_are_empty() -> None:
    # La cuenta medida: una fila de experiencia sin texto y el CV con la historia.
    db = _world(
        [{"title": "Freelance", "description": "", "achievements": []}],
        [
            _cv(
                _experience(
                    "Trabajo colaborativo en equipo", "Resolución de incidencias"
                )
            )
        ],
    )

    result = await compute_match_score("p1", "j1", db)

    assert result.score_breakdown["sub_scores"]["soft"] >= 1.0 - 1e-9
    assert result.score_breakdown["soft"]["detected"] == [
        "collaboration",
        "problem_solving",
    ]
    assert db.tables["master_profiles"][0]["inferred_soft_skills"] == [
        "collaboration",
        "problem_solving",
    ]


@pytest.mark.asyncio
async def test_the_match_scores_zero_when_nobody_says_it() -> None:
    db = _world(
        [{"title": "Freelance", "description": "", "achievements": []}],
        [_cv(_experience("Hice reportes mensuales"))],
    )

    result = await compute_match_score("p1", "j1", db)

    assert result.score_breakdown["sub_scores"]["soft"] == 0.0
