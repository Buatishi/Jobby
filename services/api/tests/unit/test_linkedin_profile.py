"""El PDF de LinkedIn de la persona y la URL de su perfil.

La web no tenía dónde cargarlos, así que el 18 % del porcentaje (12 del documento y 6 de
la URL) era inalcanzable y el kit de entrevista, que pide 100 %, no se podía generar. El
parser trataba todo documento como CV (`in_cv` en verdadero), así que un PDF de LinkedIn
habría marcado como «del CV» skills que no salen de él.

Regla elegida: el PDF de LinkedIn solo marca `in_linkedin` en las skills que la persona
ya tiene. No agrega skills (el motor de comparación usa todas las guardadas) ni calcula
vectores.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.cv_parser import skills_named_in_linkedin
from app.services.cv_parser.ai_structurer import CVStructuredData, ParsedSkill
from app.tasks import parsing
from tests.fakes import FakeSupabase

STORED_VECTOR = [0.5] * 4


def _row(skill_id: str, name: str, **overrides: Any) -> dict[str, Any]:
    return {
        "id": skill_id,
        "profile_id": "profile-1",
        "name": name,
        "category": "technical",
        "level": None,
        "in_cv": True,
        "in_linkedin": False,
        "confirmed": False,
        "embedding": STORED_VECTOR,
        **overrides,
    }


def _parsed(*names: str) -> CVStructuredData:
    return CVStructuredData(
        skills=[
            ParsedSkill(name=name, category="other", level="intermediate")
            for name in names
        ]
    )


# --- qué skills marca el PDF ---------------------------------------------------


def test_the_pdf_marks_the_skills_the_person_already_has() -> None:
    existing = [_row("s1", "Python"), _row("s2", "SQL"), _row("s3", "Docker")]

    ids = skills_named_in_linkedin(_parsed("python", "Docker"), existing)

    assert ids == ["s1", "s3"]


def test_the_match_ignores_accents_case_spaces_and_category() -> None:
    existing = [
        _row("s1", "Gestión de proyectos", category="soft"),
        _row("s2", " Node.JS "),
    ]

    ids = skills_named_in_linkedin(
        _parsed("gestion de  proyectos", "node.js"), existing
    )

    assert ids == ["s1", "s2"]


def test_skills_only_in_linkedin_are_not_added() -> None:
    assert skills_named_in_linkedin(_parsed("Kubernetes"), [_row("s1", "Python")]) == []


def test_an_already_marked_skill_is_not_written_again() -> None:
    existing = [_row("s1", "Python", in_linkedin=True), _row("s2", "SQL")]

    assert skills_named_in_linkedin(_parsed("Python", "SQL"), existing) == ["s2"]


def test_rows_without_an_id_are_skipped() -> None:
    assert skills_named_in_linkedin(_parsed("Python"), [{"name": "Python"}]) == []


# --- el parseo de un documento de LinkedIn --------------------------------------


class ExplodingGateway:
    """Un PDF de LinkedIn no necesita vectores: si se piden, la prueba falla."""

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        raise AssertionError("El PDF de LinkedIn no debería calcular vectores.")


def _world(document_type: str) -> FakeSupabase:
    supabase = FakeSupabase()
    supabase.storage.files["user-1/linkedin.pdf"] = b"%PDF-1.4 fake"
    supabase.tables["uploaded_documents"].append(
        {
            "id": "document-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": document_type,
            "storage_path": "user-1/linkedin.pdf",
            "status": "pending",
        }
    )
    supabase.tables["skills"].extend(
        [
            _row("s-python", "Python", confirmed=True),
            _row("s-sql", "SQL"),
            _row("s-docker", "Docker"),
        ]
    )
    return supabase


def _use_parser(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    async def fake_extract_pdf_text(_path: Any) -> str:
        return "texto del perfil de LinkedIn"

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return _parsed(*names)

    monkeypatch.setattr(parsing, "extract_pdf_text", fake_extract_pdf_text)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)


def _skill(supabase: FakeSupabase, skill_id: str) -> dict[str, Any]:
    return next(row for row in supabase.tables["skills"] if row["id"] == skill_id)


@pytest.mark.asyncio
async def test_a_linkedin_document_marks_in_linkedin_and_leaves_in_cv_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world("linkedin")
    _use_parser(monkeypatch, "Python", "SQL", "Kubernetes")

    result = await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=ExplodingGateway(),  # type: ignore[arg-type]
    )

    assert _skill(supabase, "s-python")["in_linkedin"] is True
    assert _skill(supabase, "s-sql")["in_linkedin"] is True
    assert _skill(supabase, "s-docker")["in_linkedin"] is False
    # `in_cv` y `confirmed` quedan como estaban, y no se agregó «Kubernetes».
    assert _skill(supabase, "s-python")["in_cv"] is True
    assert _skill(supabase, "s-python")["confirmed"] is True
    assert len(supabase.tables["skills"]) == 3
    assert result["matched_skills"] == 2
    document = supabase.tables["uploaded_documents"][0]
    assert document["status"] == "done"
    assert document["parsed_data"]["matched_skills"] == 2


@pytest.mark.asyncio
async def test_a_linkedin_document_stores_no_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world("linkedin")
    _use_parser(monkeypatch, "Python")

    await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=ExplodingGateway(),  # type: ignore[arg-type]
    )

    assert "embedding" not in str(supabase.tables["uploaded_documents"][0])


@pytest.mark.asyncio
async def test_a_cv_still_marks_in_cv_and_keeps_the_linkedin_mark(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world("cv")
    supabase.tables["skills"][1]["in_linkedin"] = True  # SQL, de un PDF anterior
    _use_parser(monkeypatch, "Python", "Terraform")

    class VectorGateway:
        async def embed_many(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] * 4 for _text in texts]

    await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=VectorGateway(),  # type: ignore[arg-type]
    )

    terraform = next(
        row for row in supabase.tables["skills"] if row["name"] == "Terraform"
    )
    assert terraform["in_cv"] is True
    assert terraform["in_linkedin"] is False
    # Un CV nuevo no apaga lo que dejó el PDF de LinkedIn.
    assert _skill(supabase, "s-sql")["in_linkedin"] is True


@pytest.mark.asyncio
async def test_a_linkedin_document_recalculates_the_percentage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world("linkedin")
    supabase.tables["master_profiles"][0]["completeness_pct"] = 0
    _use_parser(monkeypatch, "Python", "SQL", "Docker")

    await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=ExplodingGateway(),  # type: ignore[arg-type]
    )

    # 8 del headline que ya traía el perfil y 12 del documento (3 skills nombradas).
    assert supabase.tables["master_profiles"][0]["completeness_pct"] == 8 + 12


# --- la ruta -------------------------------------------------------------------


async def _current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1", supabase_uid="auth-user-1", email="person@example.com"
    )


@pytest.fixture()
def linkedin_world() -> FakeSupabase:
    supabase = FakeSupabase()
    supabase.tables["master_profiles"][0]["linkedin_url"] = (
        "https://www.linkedin.com/in/juan-perez"
    )
    supabase.tables["skills"].extend(
        [
            _row("s1", "Python", in_linkedin=True),
            _row("s2", "SQL", in_linkedin=True),
            _row("s3", "Docker"),
        ]
    )
    supabase.tables["uploaded_documents"].extend(
        [
            {
                "id": "cv-1",
                "user_id": "user-1",
                "profile_id": "profile-1",
                "type": "cv",
                "status": "done",
                "original_filename": "cv.pdf",
                "created_at": "2026-10-01T10:00:00Z",
                "parsed_data": {"summary": "DATO-DEL-CV"},
            },
            {
                "id": "in-1",
                "user_id": "user-1",
                "profile_id": "profile-1",
                "type": "linkedin",
                "status": "done",
                "original_filename": "Profile.pdf",
                "created_at": "2026-10-10T10:00:00Z",
                "parsed_data": {"summary": "DATO-DE-LINKEDIN"},
            },
        ]
    )

    async def fake_client() -> FakeSupabase:
        return supabase

    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    return supabase


def test_the_status_shows_the_url_the_document_and_the_skills_it_named(
    client: TestClient, linkedin_world: FakeSupabase
) -> None:
    response = client.get("/api/v1/profiles/linkedin")

    assert response.status_code == 200
    assert response.json() == {
        "profile_id": "profile-1",
        "linkedin_url": "https://www.linkedin.com/in/juan-perez",
        "document": {
            "id": "in-1",
            "status": "done",
            "original_filename": "Profile.pdf",
            "error_msg": None,
            "created_at": "2026-10-10T10:00:00Z",
        },
        "skills_in_linkedin": 2,
    }


def test_the_status_never_includes_parsed_data_or_vectors(
    client: TestClient, linkedin_world: FakeSupabase
) -> None:
    response = client.get("/api/v1/profiles/linkedin")

    assert "DATO-DE-LINKEDIN" not in response.text
    assert "DATO-DEL-CV" not in response.text
    assert "embedding" not in response.text


def test_the_status_of_a_profile_without_linkedin_is_empty(client: TestClient) -> None:
    supabase = FakeSupabase()

    async def fake_client() -> FakeSupabase:
        return supabase

    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.get("/api/v1/profiles/linkedin")

    assert response.status_code == 200
    assert response.json() == {
        "profile_id": "profile-1",
        "linkedin_url": None,
        "document": None,
        "skills_in_linkedin": 0,
    }


def test_a_new_linkedin_pdf_replaces_the_previous_one(
    client: TestClient,
    linkedin_world: FakeSupabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.tasks.parsing.enqueue_parse_cv", lambda _document_id, _owner: "task-1"
    )

    response = client.post(
        "/api/v1/profiles/documents",
        json={
            "profile_id": "profile-1",
            "type": "linkedin",
            "storage_path": "auth-user-1/nuevo.pdf",
            "original_filename": "Nuevo.pdf",
            "mime_type": "application/pdf",
            "file_size": 1000,
        },
    )

    assert response.status_code == 201
    linkedin_documents = [
        row
        for row in linkedin_world.tables["uploaded_documents"]
        if row["type"] == "linkedin"
    ]
    assert len(linkedin_documents) == 1
    assert linkedin_documents[0]["original_filename"] == "Nuevo.pdf"
    # El CV no se toca.
    assert any(
        row["id"] == "cv-1" for row in linkedin_world.tables["uploaded_documents"]
    )
