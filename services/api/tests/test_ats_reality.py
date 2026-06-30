import json

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.ats_analyzer.keyword_matcher import (
    ATSKeywordResult,
    KeywordMatch,
    analyze_keywords,
)
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


def test_ats_optimize_requires_premium(client: TestClient) -> None:
    fake_supabase = FakeSupabase()

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.post("/api/v1/ats/optimize", json={"job_id": "job-1"})

    assert response.status_code == 403
    assert response.json()["code"] == "PREMIUM_REQUIRED"


def test_ats_optimize_returns_rewritten_sections(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["users"][0]["tier"] = "premium"
    fake_supabase.tables["job_descriptions"].append(
        {
            "id": "job-1",
            "user_id": "user-1",
            "required_skills": ["Python", "FastAPI"],
            "tech_stack": [],
            "raw_text": "Python FastAPI backend role",
        }
    )
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "doc-1",
            "user_id": "user-1",
            "type": "cv",
            "is_primary": True,
            "parsed_data": {"skills": [{"name": "Python"}], "format_flags": {}},
        }
    )

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    async def fake_optimize(
        *_args: object,
        **_kwargs: object,
    ) -> list[dict[str, object]]:
        return [
            {
                "section_name": "skills",
                "original_excerpt": "Python",
                "rewritten_text": "Python, FastAPI",
                "added_keywords": ["FastAPI"],
                "rationale": "Cubre keyword faltante.",
            }
        ]

    async def fake_analyze_keywords(
        *_args: object,
        **_kwargs: object,
    ) -> ATSKeywordResult:
        return ATSKeywordResult(
            keywords=["FastAPI"],
            matches=[
                KeywordMatch(
                    keyword="FastAPI",
                    status="missing",
                    matched_text=None,
                )
            ]
        )

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    monkeypatch.setattr("app.api.v1.ats.optimize_cv_sections", fake_optimize)
    monkeypatch.setattr("app.api.v1.ats.analyze_keywords", fake_analyze_keywords)

    response = client.post("/api/v1/ats/optimize", json={"job_id": "job-1"})

    assert response.status_code == 200
    assert response.json()["sections"][0]["rewritten_text"] == "Python, FastAPI"
