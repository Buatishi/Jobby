"""El CV guarda aparte las skills que dijo esa lectura.

`parsed_data["skills"]` del CV es la suma de todas las skills guardadas de la persona
(las de cargas anteriores y las que agregó a mano): sirve al ATS y al motor de
comparación, pero no dice qué tiene el CV de hoy. Reality Gap necesita eso para no dar
por presente en el CV una skill que ya se sacó, así que cada lectura deja además
`extracted_skills`, solo con lo que esa lectura nombró.
"""

from typing import Any

import pytest

from app.services.cv_parser import PdfContent
from app.services.cv_parser.ai_structurer import CVStructuredData, ParsedSkill
from app.tasks import parsing
from tests.fakes import FakeSupabase


class VectorGateway:
    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 4 for _text in texts]


def _world() -> FakeSupabase:
    supabase = FakeSupabase()
    supabase.storage.files["user-1/cv.pdf"] = b"%PDF-1.4 fake"
    supabase.tables["uploaded_documents"].append(
        {
            "id": "document-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": "cv",
            "storage_path": "user-1/cv.pdf",
            "status": "pending",
            "created_at": "2026-11-02T14:55:20+00:00",
        }
    )
    return supabase


def _use_parser(monkeypatch: pytest.MonkeyPatch, *skills: ParsedSkill) -> None:
    async def fake_extract_pdf_content(_path: Any) -> PdfContent:
        return PdfContent("texto del CV", None)

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return CVStructuredData(skills=list(skills))

    monkeypatch.setattr(parsing, "extract_pdf_content", fake_extract_pdf_content)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)


async def _parse(supabase: FakeSupabase) -> dict[str, Any]:
    return await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=VectorGateway(),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_the_cv_keeps_the_skills_that_this_reading_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world()
    _use_parser(
        monkeypatch,
        ParsedSkill(name="Python", category="backend", level="advanced"),
        ParsedSkill(name="Docker", category="tools", level="unknown"),
    )

    parsed = await _parse(supabase)

    assert parsed["extracted_skills"] == [
        {"name": "Python", "category": "backend", "level": "advanced"},
        {"name": "Docker", "category": "tools", "level": "unknown"},
    ]
    stored = supabase.tables["uploaded_documents"][0]["parsed_data"]
    assert stored["extracted_skills"] == parsed["extracted_skills"]


@pytest.mark.asyncio
async def test_saved_skills_from_other_uploads_do_not_enter_the_extracted_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world()
    supabase.tables["skills"].append(
        {
            "id": "s-cobol",
            "profile_id": "profile-1",
            "name": "Cobol",
            "category": "legacy",
            "level": None,
            "in_cv": True,
            "in_linkedin": False,
            "confirmed": True,
            "embedding": [0.5] * 4,
        }
    )
    _use_parser(monkeypatch, ParsedSkill(name="Python", category="backend"))

    parsed = await _parse(supabase)

    # `skills` sigue siendo la suma (lo que usan el ATS y el motor de comparación)...
    assert {skill["name"] for skill in parsed["skills"]} == {"Cobol", "Python"}
    # ...pero el CV de hoy solo nombró Python.
    assert [skill["name"] for skill in parsed["extracted_skills"]] == ["Python"]


@pytest.mark.asyncio
async def test_a_cv_that_names_no_skill_leaves_an_empty_extracted_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world()
    _use_parser(monkeypatch)

    parsed = await _parse(supabase)

    assert parsed["extracted_skills"] == []
