"""El `tech_stack` del puesto también cuenta como skill pedida (Decisión 39).

Caso medido en producción (un puesto de ingeniería de IA): `required_skills` eran
frases y no incluía «Python», que sí estaba en `tech_stack` junto con «REST APIs». El
MatchScore solo miraba `required_skills`, así que dos skills que la persona tiene no
contaban. Los datos de acá son inventados.
"""

from typing import Any

import pytest

from app.services.match_engine.s_relevance import compute_relevance
from app.services.match_engine.s_skills import (
    compute_skills_score,
    required_skill_names,
)

LONG_TASK = "Optimizing sessions, events, latency, turns, interruptions and fallbacks"


def _skills(*names: str) -> list[dict[str, Any]]:
    return [{"name": name} for name in names]


def _job(required: list[str], tech: list[str], **extra: Any) -> dict[str, Any]:
    return {"required_skills": required, "tech_stack": tech, **extra}


def test_the_tech_stack_is_added_to_the_required_skills() -> None:
    job = _job(["Backend development"], ["Python", "Docker"])

    assert required_skill_names(job) == ["backend development", "python", "docker"]


def test_a_tech_already_in_required_skills_is_not_counted_twice() -> None:
    # Por forma común: «API REST» y «REST APIs» son la misma skill.
    job = _job(["Python", "API REST"], ["python", "REST APIs", "Docker"])

    assert required_skill_names(job) == ["python", "api rest", "docker"]


def test_a_tech_repeated_in_the_stack_counts_once() -> None:
    job = _job([], ["Docker", "docker", "Python"])

    assert required_skill_names(job) == ["docker", "python"]


def test_the_stack_is_cleaned_like_the_required_skills() -> None:
    job = _job(["Python"], ["Large Language Models (LLMs)", LONG_TASK, "Junior"])

    assert required_skill_names(job) == ["python", "large language models"]


def test_the_case_measured_in_production_counts_the_skills_the_person_has() -> None:
    job = _job(
        ["Backend development", LONG_TASK],
        ["Python", "REST APIs", "Go", "MySQL"],
    )

    result = compute_skills_score(_skills("Python", "REST APIs"), job)

    # Antes: 0 de 2 (la frase larga ya no cuenta desde la limpieza, «Python» no estaba).
    assert result["score"] == pytest.approx(2 / 5)
    assert result["literal_hits"] == ["python", "rest apis"]
    assert result["missing_skills"] == ["backend development", "go", "mysql"]


def test_a_stack_the_person_does_not_have_lowers_the_score() -> None:
    # Es el costo de contar el stack completo: un puesto que lista mucha tecnología
    # que la persona no usa baja (se midió: un puesto de redes pasó de 36 a 21).
    short = _job(["Python", "Git"], [])
    long_stack = _job(["Python", "Git"], ["Kubernetes", "BGP", "VRRP", "Codex"])
    profile = _skills("Python", "Git")

    assert compute_skills_score(profile, short)["score"] == 1.0
    assert compute_skills_score(profile, long_stack)["score"] == pytest.approx(2 / 6)


def test_a_job_with_only_a_stack_is_scored_by_it() -> None:
    job = _job([], ["Python", "Docker"])

    result = compute_skills_score(_skills("Python"), job)

    assert result["score"] == pytest.approx(1 / 2)
    assert result["missing_skills"] == ["docker"]


def test_the_stack_replaces_a_list_that_was_only_sentences() -> None:
    job = _job([LONG_TASK], ["Python"])

    assert required_skill_names(job) == ["python"]


def test_sentences_with_no_stack_are_still_kept_as_they_came() -> None:
    job = _job([LONG_TASK], [])

    assert required_skill_names(job) == [LONG_TASK.lower()]
    assert compute_skills_score(_skills("Python"), job)["score"] == 0.0


def test_a_job_with_neither_keeps_its_neutral_score() -> None:
    assert compute_skills_score(_skills("Python"), _job([], []))["score"] == 0.8


def test_a_job_without_a_stack_key_is_scored_by_its_required_skills() -> None:
    job = {"required_skills": ["Python", "Docker"]}

    assert compute_skills_score(_skills("Python"), job)["score"] == pytest.approx(1 / 2)


def test_the_relevance_counts_the_stack() -> None:
    job = _job([LONG_TASK], ["Python", "FastAPI"])
    skills_result = compute_skills_score([], job)

    relevance = compute_relevance([], job, skills_result, "python fastapi")

    # Con solo `required_skills` la evidencia era 0: el puesto parecía de otra área.
    assert relevance["evidence"] == 1.0
    assert relevance["score"] == 1.0
