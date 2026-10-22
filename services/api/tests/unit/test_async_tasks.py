from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.cv_parser import FormatFlags, PdfContent
from app.services.cv_parser.ai_structurer import CVStructuredData, ParsedSkill
from app.tasks import parsing
from tests.fakes import FakeSupabase
from tests.pdf_builder import Page, Text, build_pdf


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


class FakeGateway:
    async def embed(self, _text: str) -> list[float]:
        return [0.1] * 1536

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _text in texts]


def test_create_document_enqueues_parse_task(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    enqueued: list[str] = []

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    def fake_enqueue(document_id: str, owner_id: str) -> str:
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
            "storage_path": "auth-user-1/cv.pdf",
            "original_filename": "cv.pdf",
            "mime_type": "application/pdf",
            "file_size": 1000,
        },
    )

    assert response.status_code == 201
    assert response.json()["task_id"] == "task-123"
    assert enqueued == ["uploaded_documents-1"]
    assert fake_supabase.tables["uploaded_documents"][0]["status"] == "pending"



def _document_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "profile_id": "profile-1",
        "type": "cv",
        "cv_slot": 1,
        "is_primary": True,
        "storage_path": "auth-user-1/cv.pdf",
        "original_filename": "cv.pdf",
        "mime_type": "application/pdf",
        "file_size": 1000,
        **overrides,
    }


def _no_enqueue(document_id: str, owner_id: str) -> str:
    raise AssertionError("No se debe procesar un documento rechazado.")


@pytest.mark.parametrize(
    "storage_path",
    [
        "auth-user-2/cv.pdf",
        "auth-user-1/../auth-user-2/cv.pdf",
        "auth-user-1/./cv.pdf",
        "/auth-user-1/cv.pdf",
        "auth-user-1",
        "cv.pdf",
    ],
)
def test_document_outside_the_own_folder_is_rejected(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    storage_path: str,
) -> None:
    """La API baja el archivo con la clave de servicio: una ruta ajena da otro CV."""
    fake_supabase = FakeSupabase()

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    monkeypatch.setattr(parsing, "enqueue_parse_cv", _no_enqueue)

    response = client.post(
        "/api/v1/profiles/documents",
        json=_document_payload(storage_path=storage_path),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_STORAGE_PATH"
    assert fake_supabase.tables["uploaded_documents"] == []


def test_document_for_another_persons_profile_is_not_found(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    # FakeSupabase ya trae profile-1 de user-1; profile-2 es de otra persona.
    fake_supabase.tables["master_profiles"].append(
        {"id": "profile-2", "user_id": "user-2"}
    )

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    monkeypatch.setattr(parsing, "enqueue_parse_cv", _no_enqueue)

    response = client.post(
        "/api/v1/profiles/documents",
        json=_document_payload(profile_id="profile-2"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "PROFILE_NOT_FOUND"
    assert fake_supabase.tables["uploaded_documents"] == []

def test_create_document_replaces_existing_cv_slot_before_enqueue(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "old-document",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": "cv",
            "cv_slot": 1,
            "is_primary": True,
            "storage_path": "user-1/old.pdf",
            "status": "failed",
        }
    )
    enqueued: list[str] = []

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    def fake_enqueue(document_id: str, owner_id: str) -> str:
        enqueued.append(document_id)
        return "task-retry"

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
            "storage_path": "auth-user-1/new.pdf",
            "original_filename": "new.pdf",
            "mime_type": "application/pdf",
            "file_size": 1000,
        },
    )

    assert response.status_code == 201
    assert response.json()["task_id"] == "task-retry"
    assert len(fake_supabase.tables["uploaded_documents"]) == 1
    document = fake_supabase.tables["uploaded_documents"][0]
    assert document["storage_path"] == "auth-user-1/new.pdf"
    assert enqueued == ["uploaded_documents-1"]


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

    def fake_enqueue(document_id: str, owner_id: str) -> str:
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


def test_create_profile_skill_persists_confirmed_cv_skill(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.post(
        "/api/v1/profiles/skills",
        json={
            "name": "FastAPI",
            "category": "technical",
            "level": "advanced",
            "in_cv": True,
            "confirmed": True,
        },
    )

    assert response.status_code == 201
    assert fake_supabase.tables["skills"][0]["profile_id"] == "profile-1"
    assert fake_supabase.tables["skills"][0]["confirmed"] is True


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

    flags = FormatFlags(
        has_tables=False, multi_column=True, has_images=True, headers=["PERFIL"]
    )

    async def fake_extract_pdf_content(_path: Path) -> PdfContent:
        return PdfContent("Python FastAPI", flags)

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

    monkeypatch.setattr(parsing, "extract_pdf_content", fake_extract_pdf_content)
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
    # El formato se guarda con el CV: es lo que lee el chequeo del ATS.
    assert document["parsed_data"]["format_flags"] == {
        "has_tables": False,
        "multi_column": True,
        "has_images": True,
        "headers": ["PERFIL"],
    }


def _cv_world(content: bytes, document_type: str = "cv") -> FakeSupabase:
    supabase = FakeSupabase()
    supabase.storage.files["user-1/cv.pdf"] = content
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


@pytest.mark.asyncio
async def test_a_failed_format_analysis_leaves_the_flags_out_of_the_cv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sin banderas el ATS dice «no se pudo evaluar»; con `{}` diría «sin problemas»."""
    supabase = _cv_world(b"%PDF-1.4 fake")

    async def fake_extract_pdf_content(_path: Path) -> PdfContent:
        return PdfContent("Python FastAPI", None)

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return CVStructuredData(skills=[ParsedSkill(name="Python")])

    monkeypatch.setattr(parsing, "extract_pdf_content", fake_extract_pdf_content)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)

    await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    document = supabase.tables["uploaded_documents"][0]
    assert document["status"] == "done"
    assert "format_flags" not in document["parsed_data"]


@pytest.mark.asyncio
async def test_a_linkedin_pdf_does_not_get_format_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El ATS evalúa el CV que la persona envía, no la exportación de LinkedIn."""
    supabase = _cv_world(b"%PDF-1.4 fake", document_type="linkedin")

    async def fake_extract_pdf_content(_path: Path) -> PdfContent:
        return PdfContent(
            "texto de LinkedIn",
            FormatFlags(
                has_tables=False, multi_column=True, has_images=True, headers=[]
            ),
        )

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return CVStructuredData(skills=[ParsedSkill(name="Python")])

    monkeypatch.setattr(parsing, "extract_pdf_content", fake_extract_pdf_content)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)

    await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    assert "format_flags" not in supabase.tables["uploaded_documents"][0]["parsed_data"]


@pytest.mark.asyncio
async def test_a_real_two_column_pdf_is_saved_with_its_flags_and_read_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """De punta a punta con un PDF de verdad: sin simular la lectura."""
    left = [Text(40, 60 + 14 * n, word) for n, word in enumerate(
        ["Python", "SQL", "Git", "Linux", "React", "Docker", "Redis", "AWS"]
    )]
    right = [
        Text(230, 60 + 14 * n, line)
        for n, line in enumerate(
            [
                "Desarrollador Backend en Acme",
                "Construccion de APIs con FastAPI",
                "Mantenimiento de bases PostgreSQL",
                "Integracion con servicios de pago",
                "Monitoreo y alertas en produccion",
                "Revision de codigo del equipo",
                "Mentoria a personas junior",
                "Documentacion tecnica",
            ]
        )
    ]
    supabase = _cv_world(build_pdf([Page(texts=left + right)]))
    seen: list[str] = []

    async def fake_structure_cv_text(text: str) -> CVStructuredData:
        seen.append(text)
        return CVStructuredData(skills=[ParsedSkill(name="Python")])

    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)

    await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    flags = supabase.tables["uploaded_documents"][0]["parsed_data"]["format_flags"]
    assert flags["multi_column"] is True
    assert flags["has_tables"] is False
    assert flags["has_images"] is False
    assert "Python\nSQL\nGit\nLinux\nReact\nDocker\nRedis\nAWS" in seen[0]


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
    app.dependency_overrides[get_current_user] = _fake_current_user

    response = client.get("/api/v1/tasks/user-1.task-123")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "user-1.task-123",
        "status": "done",
        "result": {"ok": True},
        "error": None,
    }
