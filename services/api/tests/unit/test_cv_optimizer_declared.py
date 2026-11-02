"""Las keywords que la persona declara saber se escriben en el CV y cuentan.

Ni el CV ni el LinkedIn las respaldan: las responde ella (Decisión 24). El servidor
solo acepta nombres que el reporte da por faltantes, las escribe en las habilidades
(nunca en una experiencia) y las muestra aparte de las que el CV sí respalda.
"""

import json
from typing import Any

import pytest

from app.models.ats import (
    ATSKeywordMatch,
    ATSOptimizeRequest,
    ATSRequirement,
    OptimizedCVSection,
)
from app.services.ats_analyzer.cv_optimizer import (
    declared_keywords,
    ensure_declared_written,
    optimize_cv_sections,
    score_after_optimization,
    verify_sections,
)

MATCHES = [
    ATSKeywordMatch(keyword="Python", status="literal", matched_text="Python"),
    ATSKeywordMatch(keyword="FastAPI", status="literal", matched_text="FastAPI"),
    ATSKeywordMatch(keyword="CI/CD", status="missing"),
    ATSKeywordMatch(keyword="Django", status="missing"),
    ATSKeywordMatch(keyword="AI", status="missing", priority="nice"),
]
CV = {
    "parsed_data": {
        "summary": "Desarrollador full-stack con Python y FastAPI.",
        "skills": [
            {"name": "Python"},
            {"name": "FastAPI"},
            {"name": "python"},
            {"name": "Docker"},
        ],
        "experiences": [
            {
                "title": "Desarrollador Freelance",
                "company": "Pyme",
                "description": "Pipeline de facturas en Python.",
                "achievements": [],
            }
        ],
        "educations": [],
        "certifications": [],
    }
}
CV_TEXT = "Python, FastAPI, Docker"
EVIDENCE = ["Python", "FastAPI", "Docker", "Pipeline de facturas en Python."]


def _skills(text: str) -> OptimizedCVSection:
    return OptimizedCVSection(
        section_name="skills",
        original_excerpt="Python, FastAPI, Docker",
        rewritten_text=text,
        added_keywords=[],
        rationale="Cubre el puesto.",
    )


def _no_requirements() -> list[ATSRequirement]:
    return []


# --- Qué palabras se aceptan -------------------------------------------------------


def test_only_keywords_the_report_marks_missing_are_accepted() -> None:
    accepted = declared_keywords(
        MATCHES, ["ci/cd", "Python", "Kubernetes", "  django "]
    )

    # «Python» ya figura en el CV y «Kubernetes» no es del puesto: no entran.
    assert accepted == ["CI/CD", "Django"]


def test_the_report_spelling_is_what_goes_on() -> None:
    assert declared_keywords(MATCHES, ["DJANGO"]) == ["Django"]


def test_nothing_declared_is_nothing_accepted() -> None:
    assert declared_keywords(MATCHES, []) == []


def test_the_request_limits_how_many_and_how_long() -> None:
    assert ATSOptimizeRequest(job_id="job-1").confirmed_keywords == []
    with pytest.raises(ValueError):
        ATSOptimizeRequest(job_id="job-1", confirmed_keywords=["x"] * 31)
    with pytest.raises(ValueError):
        ATSOptimizeRequest(job_id="job-1", confirmed_keywords=["x" * 81])


# --- Se escriben en las habilidades, aunque la IA las omita -------------------------


def test_a_declared_keyword_the_ai_skipped_is_added_to_its_skills_section() -> None:
    [section] = ensure_declared_written(
        [_skills("Python, FastAPI, Docker")], ["CI/CD"], CV
    )

    assert section.rewritten_text == "Python, FastAPI, Docker, CI/CD"


def test_one_the_ai_already_wrote_is_not_repeated() -> None:
    [section] = ensure_declared_written(
        [_skills("Python, FastAPI, Docker, CI/CD")], ["CI/CD"], CV
    )

    assert section.rewritten_text == "Python, FastAPI, Docker, CI/CD"


def test_without_a_skills_section_one_is_made_from_the_cv_skills() -> None:
    summary = OptimizedCVSection(
        section_name="summary",
        original_excerpt="Desarrollador full-stack con Python y FastAPI.",
        rewritten_text="Desarrollador full-stack, Python y FastAPI.",
        added_keywords=[],
        rationale="Resumen.",
    )

    sections = ensure_declared_written([summary], ["CI/CD", "Django"], CV)

    assert sections[0] == summary
    skills = sections[1]
    assert skills.section_name == "skills"
    # Una vez cada habilidad (el CV trae «python» repetida), y las declaradas al final.
    assert skills.original_excerpt == "Python, FastAPI, Docker"
    assert skills.rewritten_text == "Python, FastAPI, Docker, CI/CD, Django"


def test_a_declared_keyword_never_goes_inside_an_experience() -> None:
    experience = OptimizedCVSection(
        section_name="experiences",
        target_id="exp-1",
        original_excerpt="Pipeline de facturas en Python.",
        rewritten_text="Pipeline de facturas en Python.",
        added_keywords=[],
        rationale="Viñetas.",
    )

    sections = ensure_declared_written([experience], ["CI/CD"], CV)

    assert sections[0].rewritten_text == "Pipeline de facturas en Python."
    assert "CI/CD" in sections[1].rewritten_text
    assert sections[1].section_name == "skills"


def test_nothing_declared_leaves_the_sections_as_they_were() -> None:
    sections = [_skills("Python, FastAPI")]

    assert ensure_declared_written(sections, [], CV) == sections


# --- Cuentan, y se muestran aparte --------------------------------------------------


def test_a_declared_keyword_is_noted_apart_and_is_not_unverified() -> None:
    [section] = verify_sections(
        [_skills("Python, FastAPI, CI/CD, Django")],
        MATCHES,
        CV_TEXT,
        EVIDENCE,
        declared=["CI/CD"],
    )

    assert section.declared_keywords == ["CI/CD"]
    # «Django» la escribió la IA sin que nadie la declare: sigue sin respaldo.
    assert section.unverified_keywords == ["Django"]


def test_a_declared_keyword_is_not_also_listed_as_added() -> None:
    skills = _skills("Python, CI/CD").model_copy(update={"added_keywords": ["CI/CD"]})

    [section] = verify_sections(
        [skills], MATCHES, CV_TEXT, EVIDENCE, declared=["CI/CD"]
    )

    assert section.added_keywords == []
    assert section.declared_keywords == ["CI/CD"]


def test_a_declared_keyword_the_text_does_not_write_is_not_noted() -> None:
    [section] = verify_sections(
        [_skills("Python, FastAPI")],
        MATCHES,
        CV_TEXT,
        EVIDENCE,
        declared=["CI/CD"],
    )

    assert section.declared_keywords == []


def test_declared_keywords_raise_the_score_after() -> None:
    plain = verify_sections([_skills("Python, FastAPI")], MATCHES, CV_TEXT, EVIDENCE)
    stated = verify_sections(
        [_skills("Python, FastAPI, CI/CD, Django")],
        MATCHES,
        CV_TEXT,
        EVIDENCE,
        declared=["CI/CD", "Django"],
    )

    before = score_after_optimization(plain, MATCHES, _no_requirements())
    after = score_after_optimization(stated, MATCHES, _no_requirements())

    assert after > before


def test_writing_an_undeclared_missing_keyword_still_adds_nothing() -> None:
    written = verify_sections(
        [_skills("Python, FastAPI, CI/CD, Django")], MATCHES, CV_TEXT, EVIDENCE
    )
    plain = verify_sections([_skills("Python, FastAPI")], MATCHES, CV_TEXT, EVIDENCE)

    assert score_after_optimization(
        written, MATCHES, _no_requirements()
    ) == score_after_optimization(plain, MATCHES, _no_requirements())


def test_a_nice_to_have_keyword_counts_half_of_a_required_one() -> None:
    required = verify_sections(
        [_skills("Python, FastAPI, CI/CD")],
        MATCHES,
        CV_TEXT,
        EVIDENCE,
        declared=["CI/CD"],
    )
    nice = verify_sections(
        [_skills("Python, FastAPI, AI")],
        MATCHES,
        CV_TEXT,
        EVIDENCE,
        declared=["AI"],
    )
    base = score_after_optimization(
        verify_sections([_skills("Python, FastAPI")], MATCHES, CV_TEXT, EVIDENCE),
        MATCHES,
        _no_requirements(),
    )

    gain_required = (
        score_after_optimization(required, MATCHES, _no_requirements()) - base
    )
    gain_nice = score_after_optimization(nice, MATCHES, _no_requirements()) - base

    assert 0 < gain_nice < gain_required


# --- El pedido a la IA --------------------------------------------------------------


class _RecordingGateway:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate(
        self,
        _task_type: str,
        _user_tier: str,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        self.prompts.append(prompt)
        return json.dumps(self.response)


SKILLS_RESPONSE = {
    "sections": [
        {
            "section_name": "skills",
            "original_excerpt": "Python, FastAPI, Docker",
            "rewritten_text": "Python, FastAPI, Docker",
            "added_keywords": [],
            "rationale": "Habilidades.",
        }
    ]
}


@pytest.mark.asyncio
async def test_the_prompt_lists_the_declared_keywords_and_where_they_may_go() -> None:
    gateway = _RecordingGateway(SKILLS_RESPONSE)

    await optimize_cv_sections(
        CV,
        {"job_title": "Python"},
        MATCHES,
        "free",
        gateway,
        declared=["CI/CD"],  # type: ignore[arg-type]
    )

    [prompt] = gateway.prompts
    assert "DECLARED_KEYWORDS" in prompt
    assert '["CI/CD"]' in prompt
    assert "No las pongas dentro de una experiencia" in prompt


@pytest.mark.asyncio
async def test_without_declared_keywords_the_prompt_is_the_one_it_always_was() -> None:
    gateway = _RecordingGateway(SKILLS_RESPONSE)

    await optimize_cv_sections(
        CV,
        {"job_title": "Python"},
        MATCHES,
        "free",
        gateway,  # type: ignore[arg-type]
    )

    [prompt] = gateway.prompts
    assert "DECLARED_KEYWORDS" not in prompt


@pytest.mark.asyncio
async def test_the_whole_run_writes_the_declared_keyword_and_counts_it() -> None:
    gateway = _RecordingGateway(SKILLS_RESPONSE)  # la IA no menciona «CI/CD»

    sections = await optimize_cv_sections(
        CV,
        {"job_title": "Python"},
        MATCHES,
        "free",
        gateway,
        declared=["CI/CD"],  # type: ignore[arg-type]
    )

    [skills] = sections
    assert skills.rewritten_text == "Python, FastAPI, Docker, CI/CD"
    assert skills.declared_keywords == ["CI/CD"]
    assert skills.unverified_keywords == []
    assert score_after_optimization(
        sections, MATCHES, _no_requirements()
    ) > score_after_optimization(
        verify_sections([_skills("Python, FastAPI")], MATCHES, CV_TEXT, EVIDENCE),
        MATCHES,
        _no_requirements(),
    )
