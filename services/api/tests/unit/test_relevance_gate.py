"""La compuerta de relevancia llega a pleno con la cuarta parte de las skills pedidas.

Actualización de la Decisión 29. Era el 40 %: con el stack del puesto y las skills ya
limpias (Decisión 39) un puesto con 20 skills pedidas exigía 8 en el perfil para no
atenuarse. Lo que no cambia es el piso (0,15) ni que un puesto de otra área siga
atenuado al máximo. Los datos de acá son inventados.
"""

from typing import Any

import pytest

from app.services.match_engine import compute_match_score
from app.services.match_engine.formula import _weighted_score
from app.services.match_engine.s_relevance import (
    FULL_RELEVANCE_AT,
    RELEVANCE_FLOOR,
    compute_relevance,
)
from tests.fakes import FakeSupabase


def test_the_gate_values_are_the_ones_of_the_decision() -> None:
    assert FULL_RELEVANCE_AT == 0.25
    assert RELEVANCE_FLOOR == 0.15


def test_a_quarter_of_the_required_skills_is_already_the_area() -> None:
    job = {"required_skills": ["a", "b", "c", "d"], "job_title": "x"}

    relevance = compute_relevance([], job, {"score": 0.25})

    assert relevance["score"] == 1.0
    assert relevance["evidence"] == 0.25


def test_less_than_a_quarter_is_still_attenuated() -> None:
    job = {"required_skills": ["a", "b", "c", "d", "e"], "job_title": "x"}

    one_in_five = compute_relevance([], job, {"score": 0.2})

    # 0,2 de 0,25 = 0,8 del camino entre el piso y la relevancia plena.
    assert one_in_five["score"] == pytest.approx(RELEVANCE_FLOOR + 0.8 * 0.85)


def test_with_no_overlap_the_relevance_is_the_floor() -> None:
    job = {"required_skills": ["a", "b"], "job_title": "x"}

    assert compute_relevance([], job, {"score": 0.0})["score"] == RELEVANCE_FLOOR


def _world(required: list[str]) -> FakeSupabase:
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
    db.tables["skills"] = [
        {
            "id": f"s{index}",
            "profile_id": "p1",
            "name": name,
            "category": "technical",
            "confirmed": True,
            "in_cv": True,
            "embedding": None,
        }
        for index, name in enumerate(["python", "sql", "docker", "aws"])
    ]
    db.tables["educations"] = []
    db.tables["languages"] = []
    db.tables["experiences"] = []
    db.tables["uploaded_documents"] = []
    db.tables["job_descriptions"] = [
        {
            "id": "j1",
            "user_id": "u1",
            "job_title": "Puesto",
            "raw_text": None,
            "required_seniority": "senior",
            "required_modality": "onsite",
            "industry": "software",
            "tech_stack": [],
            "required_skills": required,
            "soft_skills": [],
            "required_education": None,
            "required_languages": [],
            "embedding": None,
        }
    ]
    return db


async def _breakdown(required: list[str]) -> tuple[dict[str, Any], int, dict[str, Any]]:
    result = await compute_match_score("p1", "j1", _world(required))
    return (
        result.score_breakdown["relevance"],
        result.match_score,
        result.score_breakdown["sub_scores"],
    )


@pytest.mark.asyncio
async def test_a_job_of_the_area_with_a_quarter_of_its_skills_is_whole() -> None:
    # Python entre cuatro pedidas: 25 %.
    relevance, match_score, sub_scores = await _breakdown(
        ["python", "kubernetes", "terraform", "go"]
    )

    assert relevance["score"] == 1.0
    assert match_score == _weighted_score(sub_scores)


@pytest.mark.asyncio
async def test_a_job_of_another_area_stays_at_the_floor() -> None:
    kitchen = ["cocina internacional", "haccp", "costeo de platos", "personal"]

    relevance, match_score, sub_scores = await _breakdown(kitchen)

    assert relevance["score"] == RELEVANCE_FLOOR
    assert relevance["evidence"] == 0
    assert match_score == round(_weighted_score(sub_scores) * RELEVANCE_FLOOR)
    assert match_score <= 15
