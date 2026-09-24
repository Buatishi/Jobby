import time
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1.tasks import TASK_UNAVAILABLE_MESSAGE
from app.core.task_ids import new_task_id, task_belongs_to
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.ai_gateway.errors import ProviderUnavailableError
from app.tasks import analysis, local_fallback, parsing
from app.tasks.local_fallback import enqueue_local_task, get_local_task


async def _user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


class FakeSuccess:
    state = "SUCCESS"
    result = {"ok": True}

    def __init__(self, task_id: str, app: Any) -> None:
        self.task_id = task_id

    def ready(self) -> bool:
        return True

    def successful(self) -> bool:
        return True


class FakePending:
    state = "PENDING"
    result = None

    def __init__(self, task_id: str, app: Any) -> None:
        self.task_id = task_id

    def ready(self) -> bool:
        return False

    def successful(self) -> bool:
        return False


class FakeFailure:
    state = "FAILURE"
    result = ProviderUnavailableError(
        "openai",
        "OpenAI rechazo la API key configurada. Revisa OPENAI_API_KEY en Render.",
    )

    def __init__(self, task_id: str, app: Any) -> None:
        self.task_id = task_id

    def ready(self) -> bool:
        return True

    def successful(self) -> bool:
        return False


class ForbiddenCelery:
    def __init__(self, task_id: str, app: Any) -> None:
        raise AssertionError("No se debe consultar Celery por una tarea ajena.")


# --- ids atados al dueño (unitarios, sin I/O) -------------------------------------


def test_task_ids_are_bound_to_their_owner() -> None:
    task_id = new_task_id("user-1", "cv")

    assert task_id.startswith("user-1.cv-")
    assert task_belongs_to(task_id, "user-1")
    assert not task_belongs_to(task_id, "user-2")
    assert not task_belongs_to(task_id, "user-")
    assert not task_belongs_to("user-10.cv-abc", "user-1")
    assert not task_belongs_to(task_id, "")


def test_task_ids_are_unpredictable() -> None:
    assert new_task_id("user-1") != new_task_id("user-1")


# --- /tasks exige autenticación y solo muestra tareas propias -----------------------


def test_task_status_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/user-1.task-1")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_task_stream_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/user-1.task-1/stream")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_task_of_another_user_is_not_found_and_not_queried(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.tasks.AsyncResult", ForbiddenCelery)
    app.dependency_overrides[get_current_user] = _user

    status_response = client.get("/api/v1/tasks/user-2.task-abc")
    stream_response = client.get("/api/v1/tasks/user-2.task-abc/stream")

    assert status_response.status_code == 404
    assert status_response.json()["code"] == "TASK_NOT_FOUND"
    assert stream_response.status_code == 404


def test_task_id_without_owner_is_not_found(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.tasks.AsyncResult", ForbiddenCelery)
    app.dependency_overrides[get_current_user] = _user

    response = client.get("/api/v1/tasks/task-123")

    assert response.status_code == 404


def test_owner_reads_task_status(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.tasks.AsyncResult", FakeSuccess)
    app.dependency_overrides[get_current_user] = _user

    response = client.get("/api/v1/tasks/user-1.task-1")

    assert response.status_code == 200
    assert response.json()["status"] == "done"


def test_failed_task_does_not_leak_internal_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.tasks.AsyncResult", FakeFailure)
    app.dependency_overrides[get_current_user] = _user

    response = client.get("/api/v1/tasks/user-1.task-1")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "OPENAI_API_KEY" not in response.text
    assert "Render" not in response.text
    assert body["error"] == (
        "El servicio de IA no está disponible en este momento. "
        "Probá de nuevo más tarde."
    )


def test_stream_delivers_the_final_event_to_the_owner(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.tasks.AsyncResult", FakeSuccess)
    app.dependency_overrides[get_current_user] = _user

    with client.stream("GET", "/api/v1/tasks/user-1.task-1/stream") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "event: complete" in body
    assert '"status":"done"' in body


def test_stream_closes_when_a_task_never_finishes(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.tasks.AsyncResult", FakePending)
    monkeypatch.setattr("app.api.v1.tasks.STREAM_MAX_SECONDS", 0)
    app.dependency_overrides[get_current_user] = _user

    with client.stream("GET", "/api/v1/tasks/user-1.task-1/stream") as response:
        body = "".join(response.iter_text())

    assert "event: status" in body
    assert "event: complete" in body
    assert "tardó demasiado" in body


# --- todas las colas emiten ids atados al dueño -------------------------------------


def test_parse_cv_celery_task_id_is_bound_to_the_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_apply_async(_args: Any, **kwargs: Any) -> Any:
        return SimpleNamespace(id=kwargs["task_id"])

    monkeypatch.setattr(local_fallback.settings, "task_execution_mode", "celery")
    monkeypatch.setattr(parsing.parse_cv_task, "apply_async", fake_apply_async)

    task_id = parsing.enqueue_parse_cv("doc-1", "user-1")

    assert task_belongs_to(task_id, "user-1")
    assert task_id.startswith("user-1.cv-")


def test_parse_cv_local_fallback_keeps_the_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def broken_apply_async(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("broker down")

    def fake_local(_factory: Any, *, prefix: str, owner_id: str) -> str:
        captured["prefix"] = prefix
        captured["owner_id"] = owner_id
        return new_task_id(owner_id, prefix)

    monkeypatch.setattr(local_fallback.settings, "task_execution_mode", "celery")
    monkeypatch.setattr(parsing.parse_cv_task, "apply_async", broken_apply_async)
    monkeypatch.setattr(parsing, "enqueue_local_task", fake_local)

    task_id = parsing.enqueue_parse_cv("doc-1", "user-1")

    assert captured == {"prefix": "local-parse-cv", "owner_id": "user-1"}
    assert task_belongs_to(task_id, "user-1")


def test_job_and_kit_task_ids_are_bound_to_the_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_apply_async(_args: Any, **kwargs: Any) -> Any:
        return SimpleNamespace(id=kwargs["task_id"])

    monkeypatch.setattr(analysis.job_analysis_task, "apply_async", fake_apply_async)
    monkeypatch.setattr(analysis.interview_kit_task, "apply_async", fake_apply_async)

    job_task = analysis.enqueue_job_analysis("job-1", "user-1", "text", None, "x")
    kit_task = analysis.enqueue_interview_kit("kit-1", "user-1")

    assert job_task.startswith("user-1.job-")
    assert kit_task.startswith("user-1.kit-")


def test_local_task_ids_are_bound_to_the_owner() -> None:
    async def work() -> int:
        return 42

    task_id = enqueue_local_task(work, prefix="demo", owner_id="user-1")

    assert task_id.startswith("user-1.demo-")
    result = None
    for _ in range(300):
        result = get_local_task(task_id)
        if result is not None and result.ready():
            break
        time.sleep(0.01)
    assert result is not None
    assert result.successful()
    assert result.result == 42


def test_lost_local_task_fails_at_once_without_asking_celery(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tras un reinicio la tarea ya no está en memoria: no se espera 15 minutos."""
    monkeypatch.setattr(local_fallback.settings, "task_execution_mode", "local")
    monkeypatch.setattr("app.api.v1.tasks.AsyncResult", ForbiddenCelery)
    app.dependency_overrides[get_current_user] = _user

    status_response = client.get("/api/v1/tasks/user-1.local-job-perdida")
    stream_response = client.get("/api/v1/tasks/user-1.local-job-perdida/stream")

    assert status_response.status_code == 200
    assert status_response.json() == {
        "task_id": "user-1.local-job-perdida",
        "status": "failed",
        "result": None,
        "error": TASK_UNAVAILABLE_MESSAGE,
    }
    assert stream_response.text.startswith("event: complete")
    assert '"status":"failed"' in stream_response.text
