import json

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.ats_analyzer.keyword_matcher import analyze_keywords
from app.services.ats_analyzer.scoring import compute_ats_score
from tests.fakes import FakeSupabase


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


class FakeATSGateway:
    async def generate(
        self,
        _task_type: str,
        _user_tier: str,
        _prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        return json.dumps({"keywords": ["Python", "FastAPI"]})

    async def embed(self, text: str) -> list[float]:
        if text.lower() in {"python", "fastapi"}:
            return [1.0, 0.0, 0.0]
        return [0.0, 1.0, 0.0]


@pytest.mark.asyncio
async def test_ats_scores_full_keyword_coverage() -> None:
    job = {"required_skills": ["Python", "FastAPI"], "tech_stack": []}
    primary_cv = {
        "parsed_data": {
            "skills": [{"name": "Python"}, {"name": "FastAPI"}],
            "format_flags": {},
        }
    }

    result = await analyze_keywords(job, primary_cv, gateway=FakeATSGateway())  # type: ignore[arg-type]
    score = compute_ats_score(result.matches, [])

    assert score == 100
    assert [match.status for match in result.matches] == ["literal", "literal"]


@pytest.mark.asyncio
async def test_ats_scores_zero_keyword_coverage() -> None:
    job = {"required_skills": ["Python", "FastAPI"], "tech_stack": []}
    primary_cv = {"parsed_data": {"skills": [{"name": "Java"}], "format_flags": {}}}

    result = await analyze_keywords(job, primary_cv, gateway=FakeATSGateway())  # type: ignore[arg-type]
    score = compute_ats_score(result.matches, [])

    assert score == 0
    assert [match.status for match in result.matches] == ["missing", "missing"]


def test_reality_gap_endpoint_returns_lowest_coherence_first(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["skills"].extend(
        [
            {
                "id": "skill-1",
                "profile_id": "profile-1",
                "name": "Python",
                "category": "technical",
                "in_cv": True,
                "in_linkedin": True,
                "confirmed": True,
            },
            {
                "id": "skill-2",
                "profile_id": "profile-1",
                "name": "React",
                "category": "technical",
                "in_cv": False,
                "in_linkedin": False,
                "confirmed": True,
            },
        ]
    )

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.get("/api/v1/profiles/reality-gap")

    assert response.status_code == 200
    assert response.json()["skills"][0]["name"] == "React"
    assert response.json()["skills"][0]["coherence_score"] == 20
