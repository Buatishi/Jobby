"""La verificación del CV optimizado usa el reporte ATS: no inventa ni gasta tokens."""

import json

import pytest

from app.models.ats import ATSKeywordMatch, OptimizedCVSection
from app.services.ats_analyzer.cv_optimizer import (
    optimize_cv_sections,
    score_after_optimization,
    verify_sections,
)

MATCHES = [
    ATSKeywordMatch(keyword="Python", status="literal", matched_text="Python"),
    ATSKeywordMatch(
        keyword="Power BI", status="semantic", matched_text="Looker Studio"
    ),
    ATSKeywordMatch(keyword="Kubernetes", status="missing"),
    ATSKeywordMatch(keyword="R", status="missing"),
]
CV_TEXT = "Python, SQL, Looker Studio, Git"


def _section(text: str, added: list[str]) -> OptimizedCVSection:
    return OptimizedCVSection(
        section_name="skills",
        original_excerpt="Python, SQL, Looker Studio",
        rewritten_text=text,
        added_keywords=added,
        rationale="Cubre keywords del puesto.",
    )


def test_a_keyword_with_semantic_evidence_is_kept() -> None:
    [section] = verify_sections(
        [_section("Python, SQL, Power BI (Looker Studio)", ["Power BI"])],
        MATCHES,
        CV_TEXT,
    )

    assert section.added_keywords == ["Power BI"]
    assert section.unverified_keywords == []


def test_a_missing_keyword_the_ai_declares_needs_confirmation() -> None:
    [section] = verify_sections(
        [_section("Python, Kubernetes", ["Kubernetes"])],
        MATCHES,
        CV_TEXT,
    )

    assert section.added_keywords == []
    assert section.unverified_keywords == ["Kubernetes"]


def test_a_missing_keyword_the_ai_writes_without_declaring_it_is_caught() -> None:
    [section] = verify_sections(
        [_section("Python y despliegues con Kubernetes", [])],
        MATCHES,
        CV_TEXT,
    )

    assert section.unverified_keywords == ["Kubernetes"]


def test_a_declared_keyword_missing_from_the_text_is_dropped() -> None:
    [section] = verify_sections(
        [_section("Python y SQL", ["Power BI"])],
        MATCHES,
        CV_TEXT,
    )

    assert section.added_keywords == []
    assert section.unverified_keywords == []


def test_a_keyword_outside_the_job_list_needs_backing_in_the_cv() -> None:
    [backed, invented] = verify_sections(
        [
            _section("Python, SQL y Git", ["Git"]),
            _section("Python, SQL y Terraform", ["Terraform"]),
        ],
        MATCHES,
        CV_TEXT,
    )

    assert backed.added_keywords == ["Git"]
    assert invented.added_keywords == []
    assert invented.unverified_keywords == ["Terraform"]


def test_a_short_keyword_is_not_found_inside_another_word() -> None:
    [section] = verify_sections(
        [_section("Python y React", [])],
        MATCHES,
        CV_TEXT,
    )

    assert section.unverified_keywords == []


def test_the_score_after_counts_only_verified_keywords() -> None:
    # Antes: Python literal (1) + Power BI semántica (0,5) sobre 4 = 37,5 -> 38.
    sections = [_section("Python, Power BI y Kubernetes", ["Power BI", "Kubernetes"])]

    # Después: Power BI pasa a literal (2 sobre 4 = 50); Kubernetes sigue ausente.
    assert score_after_optimization(sections, MATCHES, penalty=0) == 50
    assert score_after_optimization(sections, MATCHES, penalty=10) == 40


class _OneCallGateway:
    """Cuenta los pedidos: verificar no suma llamadas a la IA ni pide vectores."""

    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.generate_calls = 0
        self.embed_calls = 0

    async def generate(
        self,
        _task_type: str,
        _user_tier: str,
        _prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        self.generate_calls += 1
        return json.dumps(self.response)

    async def embed(self, _text: str) -> list[float]:
        self.embed_calls += 1
        return [0.0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls += 1
        return [[0.0] for _ in texts]


@pytest.mark.asyncio
async def test_the_optimizer_returns_verified_sections_with_a_single_ai_call() -> None:
    gateway = _OneCallGateway(
        {
            "sections": [
                {
                    "section_name": "skills",
                    "original_excerpt": "Python, SQL, Looker Studio",
                    "rewritten_text": "Python, SQL, Power BI y Kubernetes",
                    "added_keywords": ["Power BI", "Kubernetes"],
                    "rationale": "Cubre keywords del puesto.",
                }
            ]
        }
    )
    primary_cv = {
        "parsed_data": {
            "skills": [{"name": "Python"}, {"name": "SQL"}, {"name": "Looker Studio"}],
        }
    }

    [section] = await optimize_cv_sections(
        primary_cv,
        {"job_title": "Analista de datos"},
        MATCHES,
        gateway,  # type: ignore[arg-type]
    )

    assert section.added_keywords == ["Power BI"]
    assert section.unverified_keywords == ["Kubernetes"]
    assert gateway.generate_calls == 1
    assert gateway.embed_calls == 0
