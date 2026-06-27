from pathlib import Path
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


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


class FakeGateway:
    async def embed(self, _text: str) -> list[float]:
        return [0.1] * 1536


def test_create_document_enqueues_parse_task(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    enqueued: list[str] = []

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    def fake_enqueue(document_id: str) -> str:
        enqueued.append(document_id)
        return "task-123"

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    monkeypatch.setattr(parsing, "enqueue_parse_cv", fake_enqueue)

    response = client.post(
        "/api/v1/profiles/documents",
        json={
            "profile_id": "profile-1",
            "type": "cv",
            "cv_slot": 1,
            "is_primary": True,
            "storage_path": "user-1/cv.pdf",
            "original_filename": "cv.pdf",
            "mime_type": "application/pdf",
            "file_size": 1000,
        },
    )

    assert response.status_code == 201
    assert response.json()["task_id"] == "task-123"
    assert enqueued == ["uploaded_documents-1"]
    assert fake_supabase.tables["uploaded_documents"][0]["status"] == "pending"


def test_set_primary_document_switches_atomically_and_requeues(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["uploaded_documents"].extend(
        [
            {
                "id": "document-1",
                "user_id": "user-1",
                "profile_id": "profile-1",
                "type": "cv",
                "storage_path": "user-1/old.pdf",
                "is_primary": True,
                "status": "done",
            },
            {
                "id": "document-2",
                "user_id": "user-1",
                "profile_id": "profile-1",
                "type": "cv",
                "storage_path": "user-1/new.pdf",
                "is_primary": False,
                "status": "done",
            },
        ]
    )
    enqueued: list[str] = []

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    def fake_enqueue(document_id: str) -> str:
        enqueued.append(document_id)
        return "task-456"

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    monkeypatch.setattr(parsing, "enqueue_parse_cv", fake_enqueue)

    response = client.patch("/api/v1/profiles/documents/document-2/set-primary")

    assert response.status_code == 200
    assert response.json()["task_id"] == "task-456"
    assert enqueued == ["document-2"]
    assert fake_supabase.tables["uploaded_documents"][0]["is_primary"] is False
    assert fake_supabase.tables["uploaded_documents"][1]["is_primary"] is True
    assert fake_supabase.tables["uploaded_documents"][1]["status"] == "pending"


@pytest.mark.asyncio
async def test_run_parse_cv_updates_document_status_and_parsed_data(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
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

    async def fake_extract_pdf_text(_path: Path) -> str:
        return "Python FastAPI"

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return CVStructuredData(
            skills=[
                ParsedSkill(
                    name="Python",
                    category="technical",
                    level="advanced",
                )
            ]
        )

    monkeypatch.setattr(parsing, "extract_pdf_text", fake_extract_pdf_text)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)

    result = await parsing.run_parse_cv(
        "document-1",
        supabase=fake_supabase,
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    document = fake_supabase.tables["uploaded_documents"][0]
    assert document["status"] == "done"
    assert document["parsed_data"]["skills"][0]["name"] == "Python"
    assert result["skills"][0]["name"] == "Python"
    assert fake_supabase.tables["skills"][0]["embedding"] == [0.1] * 1536


def test_get_task_status_reads_celery_result(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAsyncResult:
        state = "SUCCESS"
        result = {"ok": True}

        def __init__(self, task_id: str, app: Any) -> None:
            self.task_id = task_id
            self.app = app

        def ready(self) -> bool:
            return True

        def successful(self) -> bool:
            return True

    monkeypatch.setattr("app.api.v1.tasks.AsyncResult", FakeAsyncResult)

    response = client.get("/api/v1/tasks/task-123")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "task-123",
        "status": "done",
        "result": {"ok": True},
        "error": None,
    }
