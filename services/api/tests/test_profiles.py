from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from tests.fakes import FakeSupabase


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


def test_get_my_profile(client: TestClient) -> None:
    fake_supabase = FakeSupabase()

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.get("/api/v1/profiles/me")

    assert response.status_code == 200
    assert response.json()["id"] == "profile-1"
    assert response.json()["headline"] == "Backend Engineer"


def test_patch_my_profile_updates_and_recomputes_completeness(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.completeness = 34

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.patch(
        "/api/v1/profiles/me",
        json={"summary": "I build async APIs.", "target_role": "Staff Engineer"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["summary"] == "I build async APIs."
    assert body["target_role"] == "Staff Engineer"
    assert body["completeness_pct"] == 34
