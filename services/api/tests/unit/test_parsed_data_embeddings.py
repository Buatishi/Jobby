"""El vector de cada skill no viaja en `parsed_data` ni en el prompt del kit.

`merge_parsed_skills` copia las filas de `skills` leídas con `select("*")`, vector
incluido. `run_parse_cv` las guardaba así en `uploaded_documents.parsed_data` (80 115
bytes en el único CV 'done' de producción) y `_cv_text` pegaba esa lista en el prompt
del kit de entrevista (Claude, plan premium), inflando tokens y costo. El vector ya
vive en la tabla `skills`: ahí se queda, y de ahí lo lee el MatchScore.
"""

import json
from typing import Any

import pytest

from app.services.ats_analyzer.keyword_matcher import _cv_terms
from app.services.cv_parser import PdfContent, strip_embeddings
from app.services.cv_parser.ai_structurer import CVStructuredData, ParsedSkill
from app.services.match_engine.formula import _representation_score
from app.tasks import analysis, parsing
from tests.fakes import FakeSupabase

# Un número reconocible: si aparece en un texto, el vector se coló.
STORED_VECTOR = [0.123456789] * 1536
FRESH_VECTOR = [0.1] * 1536
STORED_MARKER = "0.123456789"


class FakeEmbeddingGateway:
    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [FRESH_VECTOR for _text in texts]


class CapturingKitGateway:
    """Guarda el prompt que recibe el modelo y devuelve un kit mínimo válido."""

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
        return json.dumps({"overall_summary": "Buen fit."})


def _skill_row(skill_id: str, name: str, **overrides: Any) -> dict[str, Any]:
    return {
        "id": skill_id,
        "profile_id": "profile-1",
        "name": name,
        "category": "technical",
        "level": "advanced",
        "in_cv": True,
        "confirmed": False,
        "embedding": STORED_VECTOR,
        **overrides,
    }


# --- strip_embeddings -------------------------------------------------------------


def test_strip_embeddings_drops_only_the_vector_and_does_not_mutate() -> None:
    original = [_skill_row("skill-1", "Python", confirmed=True)]

    stripped = strip_embeddings(original)

    assert "embedding" not in stripped[0]
    assert stripped[0] == {
        "id": "skill-1",
        "profile_id": "profile-1",
        "name": "Python",
        "category": "technical",
        "level": "advanced",
        "in_cv": True,
        "confirmed": True,
    }
    # La fila de origen conserva el vector: lo sigue necesitando `_upsert`.
    assert original[0]["embedding"] == STORED_VECTOR


def test_strip_embeddings_lets_non_dict_items_through() -> None:
    assert strip_embeddings(["Python", {"name": "SQL", "embedding": [1.0]}]) == [
        "Python",
        {"name": "SQL"},
    ]


# --- el parseo del CV -------------------------------------------------------------


@pytest.mark.asyncio
async def test_parsed_data_does_not_keep_the_skill_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.storage.files["user-1/cv.pdf"] = b"%PDF-1.4 fake"
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "document-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": "cv",
            "storage_path": "user-1/cv.pdf",
            "status": "pending",
        }
    )
    # Skills ya guardadas, con su vector: `select("*")` las trae enteras al parseo.
    fake_supabase.tables["skills"].extend(
        [
            _skill_row("skill-python", "Python", confirmed=True),
            _skill_row("skill-sql", "SQL", in_cv=False),
        ]
    )

    async def fake_extract_pdf_content(_path: Any) -> PdfContent:
        return PdfContent("texto del CV", None)

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return CVStructuredData(
            skills=[
                ParsedSkill(name="Python", category="technical", level="expert"),
                ParsedSkill(name="Docker", category="technical", level="intermediate"),
            ]
        )

    monkeypatch.setattr(parsing, "extract_pdf_content", fake_extract_pdf_content)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)

    result = await parsing.run_parse_cv(
        "document-1",
        supabase=fake_supabase,
        gateway=FakeEmbeddingGateway(),  # type: ignore[arg-type]
    )

    stored = fake_supabase.tables["uploaded_documents"][0]["parsed_data"]
    for parsed in (stored, result):
        assert {skill["name"] for skill in parsed["skills"]} == {
            "Python",
            "SQL",
            "Docker",
        }
        assert all("embedding" not in skill for skill in parsed["skills"])
        assert '"embedding"' not in json.dumps(parsed)
        assert STORED_MARKER not in json.dumps(parsed)
    # Lo demás de la skill se conserva: la confirmación de la persona sigue ahí.
    python = next(skill for skill in stored["skills"] if skill["name"] == "Python")
    assert python["id"] == "skill-python"
    assert python["confirmed"] is True

    # El vector no se perdió: la tabla `skills` lo guarda, uno por skill.
    rows = fake_supabase.tables["skills"]
    assert len(rows) == 3
    assert all(row["embedding"] == FRESH_VECTOR for row in rows)


# --- el prompt del kit ------------------------------------------------------------


def test_cv_text_leaves_out_the_vectors_of_documents_saved_before() -> None:
    primary_cv = {
        "parsed_data": {
            "skills": [
                {"name": "Python", "level": "advanced", "embedding": STORED_VECTOR},
                "SQL",
            ],
            "experiences": [{"title": "Backend Engineer", "company": "Acme"}],
            "educations": [],
            "languages": [],
            "certifications": [],
        }
    }

    text = analysis._cv_text(primary_cv)

    assert "embedding" not in text
    assert STORED_MARKER not in text
    assert "Python" in text
    assert "advanced" in text
    assert "SQL" in text
    assert "Backend Engineer" in text
    # Limpiar el texto no toca el documento leído.
    assert "embedding" in primary_cv["parsed_data"]["skills"][0]


def test_cv_text_without_a_parsed_cv_is_unchanged() -> None:
    assert analysis._cv_text(None) == "No disponible"
    assert analysis._cv_text({"parsed_data": None}) == "No disponible"


@pytest.mark.asyncio
async def test_the_interview_kit_prompt_carries_no_skill_vector() -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["users"][0]["tier"] = "premium"
    fake_supabase.tables["job_descriptions"].append(
        {
            "id": "job-1",
            "user_id": "user-1",
            "job_title": "Backend Engineer",
            "company_name": "Acme",
            "raw_text": "Python FastAPI role",
        }
    )
    fake_supabase.tables["interview_kits"].append(
        {
            "id": "kit-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "job_id": "job-1",
            "status": "pending",
            "prep_notes": {},
        }
    )
    # Las filas de `skills` traen el vector, y el CV principal guardado antes también.
    fake_supabase.tables["skills"].append(
        _skill_row("skill-python", "Python", confirmed=True)
    )
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "doc-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": "cv",
            "is_primary": True,
            "parsed_data": {
                "skills": [_skill_row("skill-python", "Python", confirmed=True)],
                "experiences": [],
            },
        }
    )
    gateway = CapturingKitGateway()

    result = await analysis.run_interview_kit(
        "kit-1",
        "user-1",
        supabase=fake_supabase,
        gateway=gateway,  # type: ignore[arg-type]
    )

    assert result["status"] == "done"
    assert len(gateway.prompts) == 1
    prompt = gateway.prompts[0]
    assert "Python" in prompt
    assert "embedding" not in prompt
    assert STORED_MARKER not in prompt


# --- lo que lee `parsed_data["skills"]` sigue funcionando -----------------------------


def test_the_readers_of_parsed_skills_only_need_the_names() -> None:
    parsed_skills = strip_embeddings(
        [_skill_row("skill-python", "Python"), _skill_row("skill-sql", "SQL")]
    )
    primary_cv = {
        "type": "cv",
        "is_primary": True,
        "parsed_data": {"skills": parsed_skills},
    }

    # Reporte ATS: los términos del CV salen del nombre de cada skill.
    assert _cv_terms(primary_cv) == ["Python", "SQL"]

    # MatchScore (representación): una skill confirmada sin `in_cv` cuenta si su
    # nombre figura en las skills leídas del CV principal.
    confirmed = [
        {"name": "Python", "confirmed": True, "in_cv": False},
        {"name": "Rust", "confirmed": True, "in_cv": False},
    ]
    assert _representation_score(confirmed, [primary_cv]) == 50
