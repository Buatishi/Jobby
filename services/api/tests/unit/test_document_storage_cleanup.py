"""Borrar o reemplazar un documento también borra su archivo del bucket.

Antes solo se borraba la fila de `uploaded_documents`. El archivo quedaba en
`cv-documents` sin ninguna fila que lo apuntara, y al dar de baja la cuenta la fila (el
único registro de la ruta) se borraba en cascada: esos CV ya no los podía encontrar
nadie.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.tasks import parsing
from tests.fakes import FakeStorageBucket, FakeSupabase

PDF = b"%PDF-1.4 fake"


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(id="user-1", supabase_uid="auth-user-1", email="p@example.com")


def _document(document_id: str, storage_path: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": document_id,
        "user_id": "user-1",
        "profile_id": "profile-1",
        "type": "cv",
        "cv_slot": 1,
        "is_primary": True,
        "storage_path": storage_path,
        "status": "done",
        **extra,
    }


def _use(fake_supabase: FakeSupabase) -> None:
    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client


def _new_document_body(storage_path: str, **extra: Any) -> dict[str, Any]:
    return {
        "profile_id": "profile-1",
        "type": "cv",
        "cv_slot": 1,
        "is_primary": True,
        "storage_path": storage_path,
        "original_filename": "cv.pdf",
        "mime_type": "application/pdf",
        "file_size": 1000,
        **extra,
    }


def test_deleting_a_document_removes_its_file(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["uploaded_documents"].append(
        _document("doc-1", "auth-user-1/cv.pdf")
    )
    fake_supabase.storage.files["auth-user-1/cv.pdf"] = PDF
    fake_supabase.storage.files["auth-user-1/other.pdf"] = PDF
    _use(fake_supabase)

    response = client.delete("/api/v1/profiles/documents/doc-1")

    assert response.status_code == 204
    assert fake_supabase.tables["uploaded_documents"] == []
    assert list(fake_supabase.storage.files) == ["auth-user-1/other.pdf"]


def test_replacing_a_cv_slot_removes_the_previous_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["uploaded_documents"].append(
        _document("old", "auth-user-1/old.pdf")
    )
    fake_supabase.storage.files["auth-user-1/old.pdf"] = PDF
    fake_supabase.storage.files["auth-user-1/new.pdf"] = PDF
    _use(fake_supabase)
    monkeypatch.setattr(parsing, "enqueue_parse_cv", lambda *_args: "task-1")

    response = client.post(
        "/api/v1/profiles/documents", json=_new_document_body("auth-user-1/new.pdf")
    )

    assert response.status_code == 201
    assert list(fake_supabase.storage.files) == ["auth-user-1/new.pdf"]


def test_replacing_the_linkedin_pdf_removes_the_previous_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["uploaded_documents"].append(
        _document("old", "auth-user-1/linkedin-old.pdf", type="linkedin", cv_slot=None)
    )
    fake_supabase.storage.files["auth-user-1/linkedin-old.pdf"] = PDF
    fake_supabase.storage.files["auth-user-1/linkedin-new.pdf"] = PDF
    _use(fake_supabase)
    monkeypatch.setattr(parsing, "enqueue_parse_cv", lambda *_args: "task-1")

    response = client.post(
        "/api/v1/profiles/documents",
        json=_new_document_body(
            "auth-user-1/linkedin-new.pdf",
            type="linkedin",
            cv_slot=None,
            is_primary=False,
        ),
    )

    assert response.status_code == 201
    assert list(fake_supabase.storage.files) == ["auth-user-1/linkedin-new.pdf"]


def test_a_storage_failure_does_not_block_deleting_the_document(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["uploaded_documents"].append(
        _document("doc-1", "auth-user-1/cv.pdf")
    )
    fake_supabase.storage.files["auth-user-1/cv.pdf"] = PDF
    _use(fake_supabase)

    async def storage_is_down(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("Storage no responde")

    monkeypatch.setattr(FakeStorageBucket, "remove", storage_is_down)

    response = client.delete("/api/v1/profiles/documents/doc-1")

    # La fila ya no existe: el archivo sobrante lo barre la baja de la cuenta.
    assert response.status_code == 204
    assert fake_supabase.tables["uploaded_documents"] == []
