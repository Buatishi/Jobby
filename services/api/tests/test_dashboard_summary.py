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


def test_dashboard_summary_returns_profile_and_matches(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["master_profiles"][0]["completeness_pct"] = 72
    fake_supabase.tables["uploaded_documents"].append(
        {"id": "doc-1", "user_id": "user-1", "status": "processing"}
    )
    fake_supabase.tables["job_descriptions"].append(
        {
            "id": "job-1",
            "user_id": "user-1",
            "company_name": "Acme",
            "job_title": "Backend Engineer",
            "created_at": "2026-06-29T10:00:00Z",
        }
    )
    fake_supabase.tables["job_matches"].append(
        {
            "id": "match-1",
            "user_id": "user-1",
            "job_id": "job-1",
            "match_score": 86,
            "created_at": "2026-06-29T11:00:00Z",
        }
    )

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["user_name"] == "person@example.com"
    assert body["employability_score"] == 86
    assert body["completeness_pct"] == 72
    assert body["pending_analyses_count"] == 1
    assert body["latest_matches"][0]["company_name"] == "Acme"


def test_dashboard_summary_handles_missing_profile(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["master_profiles"] = []

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["completeness_pct"] == 0
    assert body["latest_matches"] == []
