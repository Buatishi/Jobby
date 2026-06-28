import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.scraper import linkedin_scraper
from app.tasks import analysis
from tests.fakes import FakeSupabase


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


class FakeInterviewGateway:
    async def generate(
        self,
        task_type: str,
        user_tier: str,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        assert task_type == "interview_kit"
        assert user_tier == "premium"
        assert json_mode is True
        return json.dumps(
            {
                "overall_summary": "Buen fit para backend.",
                "compatibility_areas": [
                    {"name": "Skills", "score": 88, "notes": "Python fuerte."}
                ],
                "strengths": [
                    {"title": "Backend", "evidence": "Experiencia con FastAPI."}
                ],
                "risks": [
                    {"title": "Producto", "mitigation": "Preparar casos de impacto."}
                ],
                "argumentario": ["Conectar experiencia backend con métricas."],
                "model_answers": [
                    {
                        "question": "Contame de un proyecto difícil.",
                        "answer": "Elegiría el parser de CVs.",
                        "evaluation_criteria": ["claridad", "impacto"],
                    }
                ],
                "candidate_questions": ["Cómo mide éxito el equipo?"],
                "action_plan": {"title": "48 horas previas", "steps": ["Repasar CV"]},
            }
        )


def _seed_premium_kit(fake_supabase: FakeSupabase) -> None:
    fake_supabase.tables["users"][0]["tier"] = "premium"
    fake_supabase.tables["master_profiles"][0]["completeness_pct"] = 100
    fake_supabase.tables["job_descriptions"].append(
        {
            "id": "job-1",
            "user_id": "user-1",
            "job_title": "Backend Engineer",
            "company_name": "Acme",
            "raw_text": "Python FastAPI role",
        }
    )
    fake_supabase.tables["interview_kits"].append(
        {
            "id": "kit-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "job_id": "job-1",
            "match_id": None,
            "status": "pending",
            "prep_notes": {
                "company_linkedin_url": "https://linkedin.com/company/acme",
                "interviewer_linkedin_url": "https://linkedin.com/in/jane",
                "interviewer_name": "Jane",
                "interviewer_role": "Hiring Manager",
            },
        }
    )
    fake_supabase.tables["skills"].append(
        {
            "id": "skill-1",
            "profile_id": "profile-1",
            "name": "Python",
            "confirmed": True,
        }
    )
    fake_supabase.tables["experiences"].append(
        {
            "id": "exp-1",
            "profile_id": "profile-1",
            "title": "Backend Engineer",
            "description": "Built APIs.",
            "achievements": ["Reduced latency"],
        }
    )
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "doc-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": "cv",
            "is_primary": True,
            "parsed_data": {"skills": [{"name": "Python"}], "experiences": []},
        }
    )


@pytest.mark.asyncio
async def test_interview_kit_task_with_linkedin_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    _seed_premium_kit(fake_supabase)

    async def fake_company(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"company_name": "Acme", "culture_signals": ["ownership"]}

    async def fake_person(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "full_name": "Jane",
            "current_role": "Hiring Manager",
            "role_type": "Hiring Manager",
            "background_summary": "Leads backend hiring.",
        }

    monkeypatch.setattr(linkedin_scraper, "scrape_company", fake_company)
    monkeypatch.setattr(linkedin_scraper, "scrape_person", fake_person)

    result = await analysis.run_interview_kit(
        "kit-1",
        "user-1",
        supabase=fake_supabase,
        gateway=FakeInterviewGateway(),  # type: ignore[arg-type]
    )

    assert result["status"] == "done"
    assert result["ai_model_used"] == "claude-sonnet-4-5"
    assert result["prep_notes"]["overall_summary"] == "Buen fit para backend."
    assert result["prep_notes"]["company_data"]["company_name"] == "Acme"


@pytest.mark.asyncio
async def test_interview_kit_task_with_scraping_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    _seed_premium_kit(fake_supabase)

    async def failed_scrape(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"scraping_failed": True, "reason": "linkedin_authwall"}

    monkeypatch.setattr(linkedin_scraper, "scrape_company", failed_scrape)
    monkeypatch.setattr(linkedin_scraper, "scrape_person", failed_scrape)

    result = await analysis.run_interview_kit(
        "kit-1",
        "user-1",
        supabase=fake_supabase,
        gateway=FakeInterviewGateway(),  # type: ignore[arg-type]
    )

    assert result["status"] == "done"
    assert result["prep_notes"]["company_data"]["scraping_failed"] is True
    assert result["prep_notes"]["interviewer_data"]["scraping_failed"] is True


def test_create_interview_kit_requires_premium(client: TestClient) -> None:
    fake_supabase = FakeSupabase()

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.post("/api/v1/interview-kits", json={"job_id": "job-1"})

    assert response.status_code == 403
    assert response.json()["code"] == "PREMIUM_REQUIRED"
