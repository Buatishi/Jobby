"""Tope diario de cargas de documentos: contra abuso, no de producto (Decisión 28).

Cada registro en `POST /profiles/documents` encola un parseo con IA que tiene costo.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.rate_limits import (
    DOCUMENT_UPLOADS_PER_DAY_FREE,
    DOCUMENT_UPLOADS_PER_DAY_PREMIUM,
)
from app.tasks import parsing
from tests.fakes import FakeRedis, FakeSupabase

URL = "/api/v1/profiles/documents"


def _setup(
    monkeypatch: pytest.MonkeyPatch, tier: str = "free"
) -> tuple[FakeSupabase, list[str]]:
    fake_supabase = FakeSupabase()
    enqueued: list[str] = []

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    async def current_user() -> CurrentUser:
        return CurrentUser(
            id="user-1",
            supabase_uid="auth-user-1",
            email="person@example.com",
            tier=tier,
        )

    def fake_enqueue(document_id: str, owner_id: str) -> str:
        enqueued.append(document_id)
        return f"task-{len(enqueued)}"

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    monkeypatch.setattr(parsing, "enqueue_parse_cv", fake_enqueue)
    return fake_supabase, enqueued


def _payload(index: int = 0, **overrides: Any) -> dict[str, Any]:
    return {
        "profile_id": "profile-1",
        "type": "cv",
        "storage_path": f"auth-user-1/{index}-cv.pdf",
        "original_filename": "cv.pdf",
        "mime_type": "application/pdf",
        "file_size": 1000,
        **overrides,
    }


def test_free_plan_registers_ten_documents_a_day_and_blocks_the_eleventh(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase, enqueued = _setup(monkeypatch)

    statuses = [
        client.post(URL, json=_payload(index)).status_code
        for index in range(DOCUMENT_UPLOADS_PER_DAY_FREE)
    ]
    blocked = client.post(URL, json=_payload(99))

    assert statuses == [201] * 10
    assert blocked.status_code == 429
    body = blocked.json()
    assert set(body) == {"error", "code", "details"}
    assert body["code"] == "DOCUMENT_UPLOAD_RATE_LIMIT_EXCEEDED"
    assert body["details"]["limit"] == 10
    assert body["details"]["reset_at"]
    # El pedido bloqueado no registra nada ni encola un parseo que cuesta.
    assert len(enqueued) == 10
    assert len(fake_supabase.tables["uploaded_documents"]) == 10


def test_premium_plan_registers_fifty_documents_a_day_and_blocks_the_next(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, enqueued = _setup(monkeypatch, tier="premium")

    statuses = [
        client.post(URL, json=_payload(index)).status_code
        for index in range(DOCUMENT_UPLOADS_PER_DAY_PREMIUM)
    ]
    blocked = client.post(URL, json=_payload(99))

    assert statuses == [201] * 50
    assert blocked.status_code == 429
    assert blocked.json()["details"]["limit"] == 50
    assert len(enqueued) == 50


def test_a_blocked_request_does_not_replace_the_cv_already_in_the_slot(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase, _ = _setup(monkeypatch)
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "old-document",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": "cv",
            "cv_slot": 1,
            "is_primary": True,
            "storage_path": "auth-user-1/old.pdf",
            "status": "done",
        }
    )
    for index in range(DOCUMENT_UPLOADS_PER_DAY_FREE):
        assert client.post(URL, json=_payload(index)).status_code == 201

    blocked = client.post(
        URL, json=_payload(99, cv_slot=1, is_primary=True)
    )

    assert blocked.status_code == 429
    old = next(
        document
        for document in fake_supabase.tables["uploaded_documents"]
        if document["id"] == "old-document"
    )
    assert old["is_primary"] is True
    assert old["storage_path"] == "auth-user-1/old.pdf"


def test_rejected_requests_do_not_spend_the_daily_quota(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeRedis,
) -> None:
    fake_supabase, _ = _setup(monkeypatch)
    # FakeSupabase ya trae profile-1 de user-1; profile-2 es de otra persona.
    fake_supabase.tables["master_profiles"].append(
        {"id": "profile-2", "user_id": "user-2"}
    )

    foreign_path = client.post(
        URL, json=_payload(storage_path="auth-user-2/cv.pdf")
    )
    foreign_profile = client.post(URL, json=_payload(profile_id="profile-2"))
    invalid_body = client.post(URL, json={"profile_id": "profile-1"})

    assert foreign_path.status_code == 400
    assert foreign_profile.status_code == 404
    assert invalid_body.status_code == 400
    assert fake_redis.values == {}


def test_a_redis_outage_does_not_block_the_upload(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El tope es contra abuso: cargar el CV no puede depender de que Redis responda."""
    fake_supabase, enqueued = _setup(monkeypatch)
    reported: list[Exception] = []

    async def broken_redis(*_args: Any, **_kwargs: Any) -> int:
        raise ConnectionError("redis caído")

    monkeypatch.setattr("app.api.v1.profiles.increment_rate_limit", broken_redis)
    monkeypatch.setattr("app.api.v1.profiles.capture_exception", reported.append)

    response = client.post(URL, json=_payload())

    assert response.status_code == 201
    assert len(enqueued) == 1
    assert len(fake_supabase.tables["uploaded_documents"]) == 1
    # Se avisa igual: una caída de Redis no pasa en silencio.
    assert [type(error) for error in reported] == [ConnectionError]
