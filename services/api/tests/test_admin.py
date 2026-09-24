"""Rol de administración: permisos leídos de la base y métricas solo agregadas."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import validate_jwt
from app.main import app
from tests.fakes import FakeSupabase

AUTH = {"Authorization": "Bearer valid-token"}

METRICS: dict[str, Any] = {
    "generated_at": "2026-09-24T02:00:00+00:00",
    "users": {
        "total": 3,
        "free": 2,
        "premium": 1,
        "new_last_7_days": 1,
        "new_last_30_days": 3,
    },
    "cvs": {"total": 4, "done": 3, "failed": 1, "in_progress": 0},
    "jobs": {"total": 5, "last_7_days": 2},
    "matches": {
        "total": 6,
        "last_7_days": 2,
        "average_score": 71,
        "rated": 2,
        "average_rating": 4.5,
    },
    "interview_kits": {"total": 1, "done": 1, "failed": 0},
    "daily_activity": [{"day": "2026-09-24", "cvs": 1, "jobs": 2, "matches": 2}],
}


async def _claims() -> dict[str, str]:
    return {
        "sub": "auth-user-1",
        "email": "person@example.com",
        "session_id": "0f6b7c2e-3d1a-4b8e-9c5f-1a2b3c4d5e6f",
    }


@pytest.fixture
def signed_in() -> FakeSupabase:
    """Sesión válida; el rol sale de la fila de `users`, como en producción."""
    fake = FakeSupabase()
    fake.admin_metrics = dict(METRICS)

    async def fake_client() -> FakeSupabase:
        return fake

    app.dependency_overrides[validate_jwt] = _claims
    app.dependency_overrides[get_supabase_client] = fake_client
    return fake


def _make_admin(fake: FakeSupabase) -> None:
    fake.tables["users"][0]["role"] = "admin"


def test_metrics_need_a_session(client: TestClient) -> None:
    response = client.get("/api/v1/admin/metrics")

    assert response.status_code == 401


def test_a_person_without_the_permission_gets_403(
    client: TestClient, signed_in: FakeSupabase
) -> None:
    response = client.get("/api/v1/admin/metrics", headers=AUTH)

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert "admin_metrics" not in signed_in.rpc_calls


def test_an_admin_gets_the_aggregated_metrics(
    client: TestClient, signed_in: FakeSupabase
) -> None:
    _make_admin(signed_in)

    response = client.get("/api/v1/admin/metrics", headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["users"]["premium"] == 1
    assert body["matches"]["average_score"] == 71
    assert body["daily_activity"] == [
        {"day": "2026-09-24", "cvs": 1, "jobs": 2, "matches": 2}
    ]
    assert signed_in.rpc_calls.count("admin_metrics") == 1


def test_fields_outside_the_model_never_reach_the_client(
    client: TestClient, signed_in: FakeSupabase
) -> None:
    """Aunque la base devolviera un dato personal, la respuesta solo lleva conteos."""
    _make_admin(signed_in)
    signed_in.admin_metrics = {
        **METRICS,
        "users": {**METRICS["users"], "emails": ["someone@example.com"]},
        "latest_cv_text": "Experiencia en...",
    }

    response = client.get("/api/v1/admin/metrics", headers=AUTH)

    assert response.status_code == 200
    assert "someone@example.com" not in response.text
    assert "latest_cv_text" not in response.text


def test_permissions_come_from_the_database_not_from_the_role_name(
    client: TestClient, signed_in: FakeSupabase
) -> None:
    """Dar el permiso al rol "user" en la tabla alcanza: no se comparan nombres."""
    signed_in.tables["role_permissions"].append(
        {"role_id": "user", "permission": "metrics:read"}
    )

    response = client.get("/api/v1/admin/metrics", headers=AUTH)

    assert response.status_code == 200


def test_an_admin_role_without_the_permission_is_rejected(
    client: TestClient, signed_in: FakeSupabase
) -> None:
    _make_admin(signed_in)
    signed_in.tables["role_permissions"] = []

    response = client.get("/api/v1/admin/metrics", headers=AUTH)

    assert response.status_code == 403


def test_missing_metrics_are_a_clean_error(
    client: TestClient, signed_in: FakeSupabase
) -> None:
    _make_admin(signed_in)
    signed_in.admin_metrics = None

    response = client.get("/api/v1/admin/metrics", headers=AUTH)

    assert response.status_code == 500
    assert response.json()["code"] == "METRICS_UNAVAILABLE"


def test_me_returns_role_plan_and_permissions(
    client: TestClient, signed_in: FakeSupabase
) -> None:
    _make_admin(signed_in)

    response = client.get("/api/v1/users/me", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == {
        "id": "user-1",
        "email": "person@example.com",
        "role": "admin",
        "tier": "free",
        "permissions": ["metrics:read"],
    }


def test_me_for_a_regular_person_has_no_permissions(
    client: TestClient, signed_in: FakeSupabase
) -> None:
    response = client.get("/api/v1/users/me", headers=AUTH)

    assert response.status_code == 200
    assert response.json()["role"] == "user"
    assert response.json()["permissions"] == []


def test_me_needs_a_session(client: TestClient) -> None:
    assert client.get("/api/v1/users/me").status_code == 401
