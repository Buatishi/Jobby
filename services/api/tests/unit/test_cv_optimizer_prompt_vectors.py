"""El prompt del optimizador de CV no lleva vectores (plan gratis, DeepSeek).

`_fetch_job` lee la fila del puesto con `select("*")`, así que `job["embedding"]` (1536
números) iba en el prompt en cada optimización, y los CV guardados antes de cortar la
fuga de `parsed_data` traían el vector dentro de cada skill. Ninguno lo usa el modelo y
todo se paga en tokens.
"""

import json
from typing import Any

import pytest

from app.models.ats import ATSKeywordMatch
from app.services.ats_analyzer import cv_optimizer
from app.services.ats_analyzer.cv_optimizer import optimize_cv_sections

# Un número reconocible: si aparece en un texto, el vector se coló.
VECTOR = [0.123456789] * 1536
MARKER = "0.123456789"

JOB = {
    "id": "job-1",
    "job_title": "Backend Engineer",
    "company_name": "Acme",
    "raw_text": "Buscamos Python y Kubernetes",
    "embedding": VECTOR,
}
PRIMARY_CV: dict[str, Any] = {
    "type": "cv",
    "is_primary": True,
    "parsed_data": {
        "skills": [
            {"name": "Python", "level": "advanced", "embedding": VECTOR},
            {"name": "SQL", "embedding": VECTOR},
        ],
        "experiences": [{"title": "Backend Engineer", "company": "Acme"}],
        "educations": [],
        "certifications": [],
    },
}
MATCHES = [
    ATSKeywordMatch(keyword="Python", status="literal", matched_text="Python"),
    ATSKeywordMatch(keyword="Kubernetes", status="missing"),
]


class CapturingGateway:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate(
        self,
        task_type: str,
        user_tier: str,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        self.prompts.append(prompt)
        return json.dumps({"sections": []})


def test_the_prompt_carries_no_vector_from_the_job_or_the_cv() -> None:
    prompt = cv_optimizer._prompt(PRIMARY_CV, JOB, MATCHES)

    assert MARKER not in prompt
    assert '"embedding"' not in prompt
    # Lo que el modelo sí necesita sigue en el prompt.
    assert "Backend Engineer" in prompt
    assert "Buscamos Python y Kubernetes" in prompt
    assert "Python" in prompt
    assert "advanced" in prompt
    assert "SQL" in prompt


def test_building_the_prompt_does_not_change_the_rows_it_reads() -> None:
    cv_optimizer._prompt(PRIMARY_CV, JOB, MATCHES)

    assert JOB["embedding"] == VECTOR
    assert PRIMARY_CV["parsed_data"]["skills"][0]["embedding"] == VECTOR


def test_the_cv_text_used_to_verify_has_no_vector() -> None:
    sections = cv_optimizer._cv_sections(PRIMARY_CV)

    assert MARKER not in json.dumps(sections)
    assert [skill["name"] for skill in sections["skills"]] == ["Python", "SQL"]


def test_a_cv_without_parsed_data_still_builds_its_sections() -> None:
    assert cv_optimizer._cv_sections({"raw_text": "Python"}) == {"raw_text": "Python"}


@pytest.mark.asyncio
async def test_the_gateway_receives_a_prompt_without_vectors() -> None:
    gateway = CapturingGateway()

    await optimize_cv_sections(
        PRIMARY_CV,
        JOB,
        MATCHES,
        "free",
        gateway=gateway,  # type: ignore[arg-type]
    )

    assert len(gateway.prompts) == 1
    assert MARKER not in gateway.prompts[0]
    assert "Kubernetes" in gateway.prompts[0]
