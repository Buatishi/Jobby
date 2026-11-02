"""`GET /profiles/reality-gap`: lo que lee de la base y lo que devuelve."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from tests.fakes import FakeSupabase, FakeTableQuery


async def _current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


def _skill(
    profile_id: str, name: str, category: str, *, confirmed: bool = False
) -> dict[str, Any]:
    return {
        "id": f"{profile_id}-{name}-{category}",
        "profile_id": profile_id,
        "name": name,
        "category": category,
        "in_cv": True,
        "in_linkedin": False,
        "confirmed": confirmed,
        "embedding": [0.5] * 4,
    }


def _document(
    profile_id: str,
    doc_type: str,
    parsed_data: dict[str, Any],
    *,
    created_at: str,
    is_primary: bool = False,
    status: str = "done",
) -> dict[str, Any]:
    return {
        "id": f"{profile_id}-{doc_type}-{created_at}",
        "profile_id": profile_id,
        "type": doc_type,
        "status": status,
        "is_primary": is_primary,
        "original_filename": f"{doc_type}.pdf",
        "created_at": created_at,
        "parsed_data": parsed_data,
    }


def _serve(fake_supabase: FakeSupabase) -> None:
    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_supabase_client] = fake_client


def test_the_endpoint_compares_the_saved_skills_with_both_documents(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["skills"].extend(
        [
            _skill("profile-1", "Python", "technical", confirmed=True),
            _skill("profile-1", "Python", "backend"),
            _skill("profile-1", "Docker", "devops"),
            _skill("profile-2", "Cobol", "legacy"),
        ]
    )
    fake_supabase.tables["rejected_skills"].append(
        {"profile_id": "profile-1", "name": "Python"}
    )
    fake_supabase.tables["uploaded_documents"].extend(
        [
            _document(
                "profile-1",
                "cv",
                {"extracted_skills": [{"name": "Python"}, {"name": "Docker"}]},
                created_at="2026-11-02T14:55:20+00:00",
                is_primary=True,
            ),
            _document(
                "profile-1",
                "linkedin",
                {"skills": [{"name": "Python"}, {"name": "Gestión de Software"}]},
                created_at="2026-10-31T22:50:32+00:00",
            ),
            # De otro perfil: no cuenta.
            _document(
                "profile-2",
                "linkedin",
                {"skills": [{"name": "Docker"}]},
                created_at="2026-11-01T00:00:00+00:00",
            ),
        ]
    )
    _serve(fake_supabase)

    response = client.get("/api/v1/profiles/reality-gap")

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == "profile-1"
    skills = {item["name"]: item for item in body["skills"]}
    assert sorted(skills) == ["Docker", "Gestión de Software", "Python"]
    assert skills["Python"]["coherence_score"] == 100
    assert skills["Python"]["rejected"] is False
    assert skills["Docker"]["in_linkedin"] is False
    assert skills["Docker"]["recommendation"] == "Agregá Docker a LinkedIn."
    only_linkedin = skills["Gestión de Software"]
    assert only_linkedin["saved"] is False
    assert only_linkedin["in_cv"] is False
    assert only_linkedin["recommendation"] == (
        "Agregá Gestión de Software al CV para alinear tus canales."
    )
    assert body["summary"] == {
        "comparable": True,
        "total": 3,
        "in_both": 1,
        "only_cv": 1,
        "only_linkedin": 1,
        "in_neither": 0,
        "score": 73,
    }
    assert body["cv"]["filename"] == "cv.pdf"
    assert body["cv"]["skills_source"] == "document"
    assert body["linkedin"]["uploaded_at"] == "2026-10-31T22:50:32+00:00"
    # Primero lo que menos coincide.
    assert [item["coherence_score"] for item in body["skills"]] == [60, 60, 100]


def test_without_documents_the_endpoint_lists_skills_and_does_not_score(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["skills"].append(_skill("profile-1", "Python", "technical"))
    _serve(fake_supabase)

    response = client.get("/api/v1/profiles/reality-gap")

    assert response.status_code == 200
    body = response.json()
    assert body["cv"] is None
    assert body["linkedin"] is None
    assert body["summary"]["comparable"] is False
    assert body["summary"]["score"] is None
    assert body["skills"][0]["name"] == "Python"
    assert body["skills"][0]["coherence_score"] is None
    assert body["skills"][0]["in_cv"] is None


def test_a_cv_read_before_the_extracted_list_is_reported_as_saved_marks(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["skills"].append(_skill("profile-1", "Python", "technical"))
    fake_supabase.tables["uploaded_documents"].extend(
        [
            _document(
                "profile-1",
                "cv",
                {"skills": [{"name": "Python"}]},
                created_at="2026-11-02T14:55:20+00:00",
                is_primary=True,
            ),
            _document(
                "profile-1",
                "linkedin",
                {"skills": []},
                created_at="2026-10-31T22:50:32+00:00",
            ),
        ]
    )
    _serve(fake_supabase)

    body = client.get("/api/v1/profiles/reality-gap").json()

    assert body["cv"]["skills_source"] == "saved"
    assert body["skills"][0]["in_cv"] is True


def test_the_endpoint_does_not_pull_the_skill_vectors(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `select("*")` trae el vector de 1536 números de cada skill: con todas las skills
    # guardadas (no solo las confirmadas) serían cientos de KB en cada visita.
    fake_supabase = FakeSupabase()
    fake_supabase.tables["skills"].append(_skill("profile-1", "Python", "technical"))
    requested: list[tuple[str, str]] = []
    original_select = FakeTableQuery.select

    def recording_select(self: FakeTableQuery, columns: str) -> FakeTableQuery:
        requested.append((self.table_name, columns))
        return original_select(self, columns)

    monkeypatch.setattr(FakeTableQuery, "select", recording_select)
    _serve(fake_supabase)

    response = client.get("/api/v1/profiles/reality-gap")

    assert response.status_code == 200
    tables = {table for table, _columns in requested}
    assert {"skills", "rejected_skills", "uploaded_documents"} <= tables
    for table, columns in requested:
        if table in {"skills", "rejected_skills", "uploaded_documents"}:
            assert "embedding" not in columns
            assert "*" not in columns
