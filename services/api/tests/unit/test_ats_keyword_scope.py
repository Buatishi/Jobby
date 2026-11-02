"""Qué cuenta como palabra clave del reporte ATS y dónde se busca (Decisión 42).

Dos fallas medidas en el reporte real de un puesto de JPMorgan el 2026-10-31:

- «English» figuraba como palabra clave faltante mientras la tarjeta de requisitos decía
  que el inglés se cumple: el idioma se evaluaba dos veces y se contradecía.
- La búsqueda miraba solo las skills, las experiencias y los estudios: no las
  certificaciones ni el resumen del CV, así que una palabra escrita ahí figuraba
  faltante.
"""

import json
import zlib
from typing import Any

import pytest

from app.services.ats_analyzer.keyword_matcher import analyze_keywords
from app.services.cv_parser import PdfContent, ai_structurer
from app.services.cv_parser.ai_structurer import (
    MAX_SUMMARY_LENGTH,
    CVStructuredData,
    ParsedSkill,
    _normalize_structured_payload,
)
from app.services.match_engine.s_languages import is_language_keyword
from app.tasks import parsing
from tests.fakes import FakeSupabase

SUMMARY = (
    "Desarrollador con experiencia en pipelines de automatización. "
    "Trabajo con FastAPI, Celery y bases de datos PostgreSQL; "
    "me interesa el diseño de servicios y la calidad del software."
)


class FakeGateway:
    """Devuelve las keywords que se le dan y vectores que no se parecen entre sí."""

    def __init__(self, keywords: list[str] | None = None) -> None:
        self.keywords = keywords or []
        self.prompts: list[str] = []
        self.embedded: list[str] = []

    async def generate(
        self,
        _task_type: str,
        _tier: str,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        self.prompts.append(prompt)
        return json.dumps({"keywords": self.keywords})

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        self.embedded.extend(texts)
        vectors = []
        for text in texts:
            vector = [0.0] * 512
            vector[zlib.crc32(text.encode()) % 512] = 1.0
            vectors.append(vector)
        return vectors


def _cv(**parsed: Any) -> dict[str, Any]:
    return {"id": "doc-1", "parsed_data": parsed}


async def _analyze(
    keywords: list[str],
    cv: dict[str, Any],
    *,
    saved: bool = False,
) -> tuple[Any, FakeGateway]:
    gateway = FakeGateway(keywords)
    result = await analyze_keywords(
        {"job_title": "Backend Engineer"},
        cv,
        gateway=gateway,  # type: ignore[arg-type]
        keywords=keywords if saved else None,
    )
    return result, gateway


# --- los idiomas no son palabras clave -------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "English",
        "Inglés",
        "inglés avanzado",
        "English (B2)",
        "Portugués nivel intermedio",
        "Spanish and English",
    ],
)
def test_a_language_with_or_without_level_is_a_language_keyword(text: str) -> None:
    assert is_language_keyword(text) is True


@pytest.mark.parametrize(
    "text",
    ["Python", "English communication", "Business analysis", "Inglés técnico", ""],
)
def test_anything_more_than_a_language_is_kept_as_a_keyword(text: str) -> None:
    assert is_language_keyword(text) is False


@pytest.mark.asyncio
async def test_languages_the_ai_returns_are_not_keywords() -> None:
    result, _ = await _analyze(
        ["Python", "English", "Inglés avanzado", "Docker"],
        _cv(skills=[{"name": "Python"}]),
    )

    assert sorted(result.keywords) == ["Docker", "Python"]
    assert [match.keyword for match in result.matches] == result.keywords


@pytest.mark.asyncio
async def test_languages_saved_by_an_old_report_are_dropped_when_it_is_recomputed() -> (
    None
):
    result, gateway = await _analyze(
        ["Python", "English", "GraphQL"], _cv(skills=[{"name": "Python"}]), saved=True
    )

    assert result.keywords == ["Python", "GraphQL"]
    # Las keywords guardadas no se vuelven a pedir a la IA.
    assert gateway.prompts == []


@pytest.mark.asyncio
async def test_a_skill_that_only_mentions_a_language_is_kept() -> None:
    result, _ = await _analyze(
        ["English communication", "Python"], _cv(skills=[{"name": "Python"}])
    )

    assert "English communication" in result.keywords


@pytest.mark.asyncio
async def test_the_prompt_no_longer_asks_for_languages_as_keywords() -> None:
    _, gateway = await _analyze(["Python"], _cv(skills=[{"name": "Python"}]))

    [prompt] = gateway.prompts
    assert "No incluyas idiomas" in prompt
    assert "certificaciones e idiomas" not in prompt


# --- la búsqueda mira certificaciones y resumen -----------------------------------


@pytest.mark.asyncio
async def test_a_certification_name_counts_as_literal_evidence() -> None:
    result, _ = await _analyze(
        ["AWS"],
        _cv(certifications=[{"name": "AWS Cloud Practitioner", "issuer": "Amazon"}]),
    )

    [match] = result.matches
    assert match.status == "literal"
    assert match.matched_text == "AWS Cloud Practitioner"


@pytest.mark.asyncio
async def test_a_word_written_in_the_summary_is_found_with_its_context() -> None:
    result, _ = await _analyze(["FastAPI"], _cv(summary=SUMMARY))

    [match] = result.matches
    assert match.status == "literal"
    assert match.matched_text is not None
    assert "FastAPI" in match.matched_text
    # Se muestra el tramo, no el párrafo entero.
    assert len(match.matched_text) < len(SUMMARY)
    assert match.matched_text.startswith("…")


@pytest.mark.asyncio
async def test_the_summary_search_uses_whole_words() -> None:
    result, _ = await _analyze(
        ["SQL", "Git"], _cv(summary="Bases de datos PostgreSQL y Digital")
    )

    assert [match.status for match in result.matches] == ["missing", "missing"]


@pytest.mark.asyncio
async def test_a_skill_of_the_cv_wins_over_the_summary() -> None:
    result, _ = await _analyze(
        ["FastAPI"], _cv(skills=[{"name": "FastAPI"}], summary=SUMMARY)
    )

    [match] = result.matches
    assert match.matched_text == "FastAPI"


@pytest.mark.asyncio
async def test_the_summary_is_never_sent_to_be_compared_by_meaning() -> None:
    result, gateway = await _analyze(
        ["Kubernetes"], _cv(skills=[{"name": "Python"}], summary=SUMMARY)
    )

    assert result.matches[0].status == "missing"
    assert SUMMARY not in gateway.embedded
    assert all(len(text) < len(SUMMARY) for text in gateway.embedded)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "summary", [None, "", "   ", 7, ["FastAPI"], {"text": "FastAPI"}]
)
async def test_a_cv_without_a_usable_summary_is_searched_as_before(
    summary: Any,
) -> None:
    result, _ = await _analyze(
        ["FastAPI"], _cv(skills=[{"name": "Python"}], summary=summary)
    )

    assert result.matches[0].status == "missing"


# --- el lector guarda el resumen ---------------------------------------------------


def test_the_reader_keeps_the_summary_on_one_line() -> None:
    normalized = _normalize_structured_payload(
        {"summary": "  Desarrollador Python.\n\nExperiencia   en   automatización.  "}
    )

    assert (
        normalized["summary"] == "Desarrollador Python. Experiencia en automatización."
    )


def test_the_reader_cuts_a_summary_that_is_too_long() -> None:
    normalized = _normalize_structured_payload({"summary": "palabra " * 1000})

    assert len(normalized["summary"]) == MAX_SUMMARY_LENGTH


@pytest.mark.parametrize("value", [None, 7, ["texto"], {"text": "texto"}, True])
def test_the_reader_ignores_a_summary_that_is_not_text(value: Any) -> None:
    assert _normalize_structured_payload({"summary": value})["summary"] == ""


def test_a_cv_without_summary_validates_as_before() -> None:
    data = CVStructuredData.model_validate(_normalize_structured_payload({}))

    assert data.summary == ""


def test_the_prompt_asks_for_the_summary_as_a_string() -> None:
    system = ai_structurer._system_prompt()
    user = ai_structurer._user_prompt("texto")

    assert "contact, summary, skills" in system
    assert "exactly as the CV writes it" in system
    assert "summary must be a string" in user


# --- el resumen llega a donde se guarda ----------------------------------------------


def _world(document_type: str) -> FakeSupabase:
    supabase = FakeSupabase()
    supabase.storage.files["user-1/cv.pdf"] = b"%PDF-1.4 fake"
    supabase.tables["uploaded_documents"].append(
        {
            "id": "document-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": document_type,
            "storage_path": "user-1/cv.pdf",
            "status": "pending",
        }
    )
    return supabase


def _use_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_extract_pdf_content(_path: Any) -> PdfContent:
        return PdfContent("texto del CV", None)

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return CVStructuredData(
            summary=SUMMARY,
            skills=[ParsedSkill(name="Python", category="other", level="advanced")],
        )

    monkeypatch.setattr(parsing, "extract_pdf_content", fake_extract_pdf_content)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)


class _VectorGateway:
    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 4 for _text in texts]


@pytest.mark.asyncio
async def test_a_cv_stores_its_summary_and_a_linkedin_pdf_does_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_parser(monkeypatch)
    cv = _world("cv")
    linkedin = _world("linkedin")

    for supabase in (cv, linkedin):
        await parsing.run_parse_cv(
            "document-1",
            supabase=supabase,
            gateway=_VectorGateway(),  # type: ignore[arg-type]
        )

    assert cv.tables["uploaded_documents"][0]["parsed_data"]["summary"] == SUMMARY
    assert "summary" not in linkedin.tables["uploaded_documents"][0]["parsed_data"]
