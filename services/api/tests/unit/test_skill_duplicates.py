"""Una skill no se duplica al reprocesar el CV ni al confirmarla (docs/03, paso 2.5).

El parseo hacía `upsert` sin `id` y el alta siempre insertaba: cada parseo dejaba una
copia nueva de cada skill y confirmar en el paso 3 sumaba otra, sin vector. Con el
cálculo del puntaje por nombre, la copia sin vector podía ocultar a la que lo tenía.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.cv_parser.ai_structurer import CVStructuredData, ParsedSkill
from app.tasks import parsing
from tests.fakes import FakeSupabase

VECTOR = [0.1] * 1536


class FakeGateway:
    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [VECTOR for _text in texts]


def _fake_with_document() -> FakeSupabase:
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
    return fake_supabase


async def _parse(
    fake_supabase: FakeSupabase,
    monkeypatch: pytest.MonkeyPatch,
    skills: list[ParsedSkill],
) -> None:
    async def fake_extract_pdf_text(_path: Any) -> str:
        return "texto del CV"

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return CVStructuredData(skills=skills)

    monkeypatch.setattr(parsing, "extract_pdf_text", fake_extract_pdf_text)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)
    await parsing.run_parse_cv(
        "document-1",
        supabase=fake_supabase,
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )


def _skill_row(skill_id: str, name: str, **overrides: Any) -> dict[str, Any]:
    return {
        "id": skill_id,
        "profile_id": "profile-1",
        "name": name,
        "category": "technical",
        "level": "advanced",
        "in_cv": True,
        "confirmed": False,
        "embedding": None,
        **overrides,
    }


# --- el parseo del CV ----------------------------------------------------------


@pytest.mark.asyncio
async def test_reprocessing_the_same_cv_does_not_duplicate_skills(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = _fake_with_document()
    parsed = [
        ParsedSkill(name="Python", category="technical", level="advanced"),
        ParsedSkill(name="FastAPI", category="technical", level="advanced"),
    ]

    await _parse(fake_supabase, monkeypatch, parsed)
    first_ids = sorted(row["id"] for row in fake_supabase.tables["skills"])
    await _parse(fake_supabase, monkeypatch, parsed)
    await _parse(fake_supabase, monkeypatch, parsed)

    skills = fake_supabase.tables["skills"]
    assert len(skills) == 2
    assert sorted(row["id"] for row in skills) == first_ids
    assert all(row["embedding"] == VECTOR for row in skills)


@pytest.mark.asyncio
async def test_the_parse_updates_the_skills_already_saved_instead_of_copying_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = _fake_with_document()
    fake_supabase.tables["skills"].extend(
        [
            _skill_row("skill-python", "Python", confirmed=True),
            _skill_row("skill-fastapi", "FastAPI"),
        ]
    )
    parsed = [
        ParsedSkill(name="Python", category="technical", level="advanced"),
        ParsedSkill(name="FastAPI", category="technical", level="expert"),
        ParsedSkill(name="Docker", category="technical", level="intermediate"),
    ]

    await _parse(fake_supabase, monkeypatch, parsed)

    skills = {row["name"]: row for row in fake_supabase.tables["skills"]}
    assert len(fake_supabase.tables["skills"]) == 3
    # La que la persona ya había confirmado sigue confirmada y gana su vector.
    assert skills["Python"]["id"] == "skill-python"
    assert skills["Python"]["confirmed"] is True
    assert skills["Python"]["embedding"] == VECTOR
    # La que el parseo había guardado se actualiza en la misma fila.
    assert skills["FastAPI"]["id"] == "skill-fastapi"
    assert skills["FastAPI"]["level"] == "expert"
    assert skills["FastAPI"]["embedding"] == VECTOR
    # Solo la nueva es una fila nueva.
    assert skills["Docker"]["confirmed"] is False
    assert skills["Docker"]["embedding"] == VECTOR


# --- confirmar en el paso 3 -----------------------------------------------------


def _use(fake_supabase: FakeSupabase) -> None:
    async def fake_client() -> FakeSupabase:
        return fake_supabase

    async def current_user() -> CurrentUser:
        return CurrentUser(
            id="user-1", supabase_uid="auth-user-1", email="person@example.com"
        )

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_supabase_client] = fake_client


def _confirm(client: TestClient, name: str = "Python", **overrides: Any) -> Any:
    return client.post(
        "/api/v1/profiles/skills",
        json={
            "name": name,
            "category": "technical",
            "level": "advanced",
            "in_cv": True,
            "confirmed": True,
            **overrides,
        },
    )


def test_confirming_a_skill_the_parse_saved_updates_that_row(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["skills"].append(
        _skill_row("skill-1", "Python", embedding=VECTOR)
    )
    _use(fake_supabase)

    # El asistente manda el nombre tal como lo extrajo la IA, a veces con otra
    # capitalización: es la misma skill.
    response = _confirm(client, name="python")

    assert response.status_code == 201
    assert response.json()["id"] == "skill-1"
    assert "embedding" not in response.json()
    assert len(fake_supabase.tables["skills"]) == 1
    row = fake_supabase.tables["skills"][0]
    assert row["confirmed"] is True
    assert row["embedding"] == VECTOR


def test_posting_the_same_skill_twice_keeps_one_row(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    _use(fake_supabase)

    first = _confirm(client)
    second = _confirm(client)

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert len(fake_supabase.tables["skills"]) == 1


def test_a_new_skill_is_still_inserted_with_its_flags(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    _use(fake_supabase)

    response = _confirm(client, name="FastAPI", confirmed=False)

    assert response.status_code == 201
    assert len(fake_supabase.tables["skills"]) == 1
    row = fake_supabase.tables["skills"][0]
    assert row["profile_id"] == "profile-1"
    assert row["confirmed"] is False
    assert row["in_cv"] is True


def test_an_alta_never_lowers_a_flag_that_was_already_set(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["skills"].append(
        _skill_row("skill-1", "Python", confirmed=True)
    )
    _use(fake_supabase)

    response = _confirm(client, confirmed=False, in_cv=False)

    assert response.status_code == 201
    row = fake_supabase.tables["skills"][0]
    assert row["confirmed"] is True
    assert row["in_cv"] is True


def test_another_persons_skill_with_the_same_name_is_not_touched(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["master_profiles"].append(
        {"id": "profile-2", "user_id": "user-2"}
    )
    fake_supabase.tables["skills"].append(
        _skill_row("skill-other", "Python", profile_id="profile-2")
    )
    _use(fake_supabase)

    response = _confirm(client)

    assert response.status_code == 201
    other = next(
        row for row in fake_supabase.tables["skills"] if row["id"] == "skill-other"
    )
    assert other["confirmed"] is False
    assert other["profile_id"] == "profile-2"
    mine = [
        row
        for row in fake_supabase.tables["skills"]
        if row["profile_id"] == "profile-1"
    ]
    assert len(mine) == 1
    assert mine[0]["id"] != "skill-other"
    assert mine[0]["confirmed"] is True
