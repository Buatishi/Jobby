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


def _seed_match(fake_supabase: FakeSupabase) -> None:
    fake_supabase.tables["job_descriptions"].append(
        {
            "id": "job-1",
            "user_id": "user-1",
            "job_title": "Backend Engineer",
            "company_name": "Acme",
            "tech_stack": ["Python"],
            "required_skills": ["Python"],
        }
    )
    fake_supabase.tables["job_matches"].append(
        {
            "id": "match-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "job_id": "job-1",
            "match_score": 82,
            "potential_score": 94,
            "representation_score": 75,
            "gap_origin": "skills",
            "score_breakdown": {"sub_scores": {"skills": 0.8}},
            "recommendations": [
                {
                    "title": "Agregá React",
                    "description": "Agregá React al CV.",
                    "priority": "high",
                }
            ],
            "user_rating": None,
            "ai_model_used": "deepseek-chat",
        }
    )


def test_get_match_report_by_job_id(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    _seed_match(fake_supabase)

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.get("/api/v1/matches/job-1")

    assert response.status_code == 200
    assert response.json()["id"] == "match-1"
    assert response.json()["job"]["job_title"] == "Backend Engineer"


def test_patch_match_rating(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    _seed_match(fake_supabase)

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.patch("/api/v1/matches/match-1/rating", json={"rating": 5})

    assert response.status_code == 200
    assert response.json()["user_rating"] == 5
    assert fake_supabase.tables["job_matches"][0]["user_rating"] == 5
