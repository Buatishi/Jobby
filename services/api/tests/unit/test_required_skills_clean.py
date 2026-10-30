"""Las skills que pide el puesto se limpian antes de compararlas (Decisión 39).

Caso medido en producción (un puesto de ingeniería de IA): la IA devolvió 17
`required_skills`, casi todas tareas escritas como frase («Familiarity with large
language models and their APIs»). Ninguna skill del perfil se llama así: el divisor
crecía y el puntaje de skills bajaba aunque la persona tuviera las que sí eran nombres.
El filtro es conservador (Decisión 35): descarta lo que pasa de 5 palabras, no una tarea
corta como «Building AI agents». Los datos de acá son inventados.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from app.services.match_engine.s_relevance import compute_relevance
from app.services.match_engine.s_skills import (
    compute_skills_score,
    required_skill_names,
)
from app.tasks import analysis

API_ROOT = Path(__file__).resolve().parents[2]

SENTENCES = [
    "Optimizing sessions, events, latency, turns, interruptions and error fallbacks",
    "Familiarity with large language models and their APIs",
    "Improving agents, prompts, tools and models",
    "Integrating voice conversational agents with specialized platforms",
]


def _skills(*names: str) -> list[dict[str, Any]]:
    return [{"name": name} for name in names]


def _job(*required: Any, **extra: Any) -> dict[str, Any]:
    return {"required_skills": list(required), "tech_stack": [], **extra}


def test_the_text_in_parentheses_is_not_part_of_the_skill_name() -> None:
    job = _job(
        "Relational databases (MySQL or similar)",
        "Asynchronous processing (queues, retries, idempotency)",
    )

    assert required_skill_names(job) == [
        "relational databases",
        "asynchronous processing",
    ]


def test_a_task_written_as_a_sentence_is_not_a_required_skill() -> None:
    job = _job("Python", *SENTENCES)

    assert required_skill_names(job) == ["python"]


def test_a_short_task_is_kept() -> None:
    # El filtro solo descarta lo que seguro no es una skill: no puede distinguir
    # «Building AI agents» de un nombre, y ante la duda la deja.
    job = _job("Python", "Building AI agents")

    assert required_skill_names(job) == ["python", "building ai agents"]


def test_the_sentences_no_longer_dilute_the_score() -> None:
    job = _job("Python", "SQL", *SENTENCES)

    result = compute_skills_score(_skills("Python", "SQL"), job)

    # Antes: 2 de 6, porque las cuatro frases nunca podían coincidir.
    assert result["score"] == 1.0
    assert result["missing_skills"] == []


def test_a_missing_skill_still_lowers_the_score() -> None:
    job = _job("Python", "Docker", *SENTENCES)

    result = compute_skills_score(_skills("Python"), job)

    assert result["score"] == pytest.approx(1 / 2)
    assert result["missing_skills"] == ["docker"]


def test_level_modality_and_title_are_not_required_skills() -> None:
    job = _job(
        "Python",
        "Junior",
        "Híbrido",
        "Desarrollador Python Jr",
        "Docker",
        job_title="Desarrollador Python Jr",
        required_seniority="Junior",
        required_modality="Híbrido (presencial en CABA)",
    )

    assert required_skill_names(job) == ["python", "docker"]


def test_the_same_name_counts_once() -> None:
    # «Docker (Compose)» queda en «Docker» al sacar el paréntesis.
    job = _job("Docker", "docker", "Docker (Compose)", "Python")

    assert required_skill_names(job) == ["docker", "python"]
    assert compute_skills_score(_skills("Python"), job)["score"] == pytest.approx(1 / 2)


def test_two_aliases_of_a_skill_still_count_each() -> None:
    # Es otra regla (Decisión de alias): «REST API» y «API REST» son nombres distintos
    # del puesto y cada uno cuenta. Limpiar la lista no la cambia.
    job = _job("REST API", "API REST", "Docker", "Kubernetes")

    result = compute_skills_score(_skills("REST APIs", "Docker"), job)

    assert result["score"] == pytest.approx(3 / 4)


def test_a_list_of_only_sentences_is_kept_as_it_came() -> None:
    # Vacía se leería como «el puesto no pide nada» y daría el 0,8 neutro.
    job = _job(*SENTENCES[:2])

    result = compute_skills_score(_skills("Python"), job)

    assert result["score"] == 0.0
    assert result["missing_skills"] == [sentence.lower() for sentence in SENTENCES[:2]]
    assert required_skill_names(job) == [sentence.lower() for sentence in SENTENCES[:2]]


def test_a_job_without_required_skills_keeps_its_neutral_score() -> None:
    assert compute_skills_score(_skills("Python"), _job())["score"] == 0.8


def test_a_skill_with_a_vector_keeps_it_when_its_name_is_cleaned() -> None:
    containers = [0.0, 1.0, 0.0]
    python = [1.0, 0.0, 0.0]
    job = _job(
        {"name": "Contenedores (Docker, Podman)", "embedding": containers},
        {"name": "Python", "embedding": python},
    )
    profile = [
        {"name": "Python", "embedding": python},
        {"name": "Docker", "embedding": containers},
    ]

    result = compute_skills_score(profile, job)

    assert required_skill_names(job) == ["contenedores", "python"]
    assert result["literal_hits"] == ["python"]
    assert result["semantic_hits"] == 1
    assert result["missing_skills"] == []


def test_the_relevance_reads_the_clean_names() -> None:
    job = _job("Python", *SENTENCES)
    skills_result = compute_skills_score([], job)

    relevance = compute_relevance([], job, skills_result, "python fastapi")

    # Con las frases en la lista era 1 de 5 menciones: el puesto parecía de otra área.
    assert relevance["evidence"] == 1.0
    assert relevance["score"] == 1.0


@pytest.mark.parametrize(
    ("first", "second"),
    [("match_engine", "ats_analyzer"), ("ats_analyzer", "match_engine")],
)
def test_the_match_engine_and_the_ats_import_in_any_order(
    first: str, second: str
) -> None:
    # El filtro vive fuera de `ats_analyzer` para que el motor no importe del ATS: el
    # ATS ya importa del motor y el ciclo rompía la importación según quién entrara
    # primero.
    result = subprocess.run(
        [sys.executable, "-c", f"import app.services.{first}, app.services.{second}"],
        cwd=API_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_the_job_prompt_asks_for_short_skill_names() -> None:
    prompt = analysis._user_prompt("Buscamos a alguien con Python.")

    assert "one skill per item" in prompt
    assert "at most 4 words" in prompt
    assert "no parentheses" in prompt
    assert "never a sentence or a task description" in prompt
    assert prompt.endswith("Buscamos a alguien con Python.")
