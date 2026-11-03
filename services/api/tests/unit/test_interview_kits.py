import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.ai_gateway.errors import ProviderUnavailableError
from app.services.scraper import linkedin_scraper
from app.tasks import analysis
from tests.fakes import FakeSupabase


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


async def _fake_premium_user() -> CurrentUser:
    """El plan llega con la sesión: get_current_user lo lee junto con el rol."""
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
        tier="premium",
    )


KIT_JSON = json.dumps(
    {
        "overall_summary": "Buen fit para backend.",
        "compatibility_areas": [
            {"name": "Skills", "score": 88, "notes": "Python fuerte."}
        ],
        "strengths": [{"title": "Backend", "evidence": "Experiencia con FastAPI."}],
        "risks": [{"title": "Producto", "mitigation": "Preparar casos de impacto."}],
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


class FakeInterviewGateway:
    async def generate(
        self,
        task_type: str,
        user_tier: str,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        fallback: bool = False,
    ) -> str:
        assert task_type == "interview_kit"
        assert user_tier == "premium"
        assert json_mode is True
        return KIT_JSON


class ScriptedKitGateway:
    """Responde por modelo: Claude (`fallback=False`) y DeepSeek (`fallback=True`)."""

    def __init__(self, claude: str | Exception, deepseek: str | Exception) -> None:
        self.replies = {False: claude, True: deepseek}
        self.calls: list[bool] = []

    async def generate(
        self,
        task_type: str,
        user_tier: str,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        fallback: bool = False,
    ) -> str:
        assert task_type == "interview_kit"
        assert user_tier == "premium"
        assert json_mode is True
        self.calls.append(fallback)
        reply = self.replies[fallback]
        if isinstance(reply, Exception):
            raise reply
        return reply


def _seed_premium_kit(fake_supabase: FakeSupabase) -> None:
    # La tarea en segundo plano no tiene sesión: lee el plan de la tabla users.
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


def _no_credit_error() -> httpx.HTTPStatusError:
    """El 400 que Anthropic devuelve cuando la cuenta no tiene saldo."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(400, request=request)
    return httpx.HTTPStatusError(
        "Client error '400 Bad Request'", request=request, response=response
    )


def _seed_kit_without_linkedin(
    monkeypatch: pytest.MonkeyPatch,
) -> FakeSupabase:
    fake_supabase = FakeSupabase()
    _seed_premium_kit(fake_supabase)

    async def failed_scrape(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"scraping_failed": True, "reason": "linkedin_authwall"}

    monkeypatch.setattr(linkedin_scraper, "scrape_company", failed_scrape)
    monkeypatch.setattr(linkedin_scraper, "scrape_person", failed_scrape)
    return fake_supabase


@pytest.mark.asyncio
async def test_interview_kit_falls_back_to_deepseek_when_claude_has_no_credit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = _seed_kit_without_linkedin(monkeypatch)
    gateway = ScriptedKitGateway(claude=_no_credit_error(), deepseek=KIT_JSON)

    result = await analysis.run_interview_kit(
        "kit-1",
        "user-1",
        supabase=fake_supabase,
        gateway=gateway,  # type: ignore[arg-type]
    )

    assert gateway.calls == [False, True]
    assert result["status"] == "done"
    assert result["ai_model_used"] == "deepseek-chat"
    assert result["prep_notes"]["overall_summary"] == "Buen fit para backend."
    assert fake_supabase.tables["interview_kits"][0]["status"] == "done"


@pytest.mark.asyncio
async def test_interview_kit_falls_back_to_deepseek_when_claude_returns_broken_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = _seed_kit_without_linkedin(monkeypatch)
    gateway = ScriptedKitGateway(claude="no es json", deepseek=KIT_JSON)

    result = await analysis.run_interview_kit(
        "kit-1",
        "user-1",
        supabase=fake_supabase,
        gateway=gateway,  # type: ignore[arg-type]
    )

    assert gateway.calls == [False, True]
    assert result["status"] == "done"
    assert result["ai_model_used"] == "deepseek-chat"


@pytest.mark.asyncio
async def test_interview_kit_does_not_call_deepseek_when_claude_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = _seed_kit_without_linkedin(monkeypatch)
    gateway = ScriptedKitGateway(claude=KIT_JSON, deepseek=_no_credit_error())

    result = await analysis.run_interview_kit(
        "kit-1",
        "user-1",
        supabase=fake_supabase,
        gateway=gateway,  # type: ignore[arg-type]
    )

    assert gateway.calls == [False]
    assert result["ai_model_used"] == "claude-sonnet-4-5"


@pytest.mark.asyncio
async def test_interview_kit_fails_with_a_clear_message_when_no_model_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = _seed_kit_without_linkedin(monkeypatch)
    gateway = ScriptedKitGateway(claude=_no_credit_error(), deepseek="tampoco es json")

    with pytest.raises(ProviderUnavailableError):
        await analysis.run_interview_kit(
            "kit-1",
            "user-1",
            supabase=fake_supabase,
            gateway=gateway,  # type: ignore[arg-type]
        )

    kit = fake_supabase.tables["interview_kits"][0]
    assert gateway.calls == [False, True]
    assert kit["status"] == "failed"
    # El detalle del proveedor (HTTP, saldo) queda en los logs, no en la respuesta.
    assert kit["error_msg"] == (
        "El servicio de IA no está disponible en este momento. "
        "Probá de nuevo más tarde."
    )


def test_create_interview_kit_requires_premium(client: TestClient) -> None:
    fake_supabase = FakeSupabase()

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.post("/api/v1/interview-kits", json={"job_id": "job-1"})

    assert response.status_code == 403
    assert response.json()["code"] == "PREMIUM_REQUIRED"


@pytest.mark.parametrize(("completeness_pct", "status_code"), [(99, 403), (100, 202)])
def test_create_interview_kit_requires_a_complete_profile(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    completeness_pct: int,
    status_code: int,
) -> None:
    fake_supabase = FakeSupabase()
    _seed_premium_kit(fake_supabase)
    fake_supabase.tables["master_profiles"][0]["completeness_pct"] = completeness_pct

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    monkeypatch.setattr(
        "app.api.v1.interview_kits.enqueue_interview_kit",
        lambda _kit_id, _user_id: "user-1.kit-test",
    )
    app.dependency_overrides[get_current_user] = _fake_premium_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.post("/api/v1/interview-kits", json={"job_id": "job-1"})

    assert response.status_code == status_code
    if status_code == 403:
        assert response.json()["code"] == "PROFILE_INCOMPLETE"


def _create_kit_client(
    monkeypatch: pytest.MonkeyPatch, fake_supabase: FakeSupabase
) -> list[str]:
    """Deja el entorno listo para crear un kit y devuelve la lista de kits encolados."""
    queued: list[str] = []

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    def fake_enqueue(kit_id: str, _user_id: str) -> str:
        queued.append(kit_id)
        return "user-1.kit-test"

    monkeypatch.setattr("app.api.v1.interview_kits.enqueue_interview_kit", fake_enqueue)
    app.dependency_overrides[get_current_user] = _fake_premium_user
    app.dependency_overrides[get_supabase_client] = fake_client
    return queued


def test_create_interview_kit_rejects_a_job_of_another_person(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_supabase = FakeSupabase()
    _seed_premium_kit(fake_supabase)
    fake_supabase.tables["job_descriptions"].append(
        {"id": "job-2", "user_id": "user-2", "job_title": "Puesto ajeno"}
    )
    kits_before = len(fake_supabase.tables["interview_kits"])
    queued = _create_kit_client(monkeypatch, fake_supabase)

    response = client.post("/api/v1/interview-kits", json={"job_id": "job-2"})

    assert response.status_code == 404
    assert response.json()["code"] == "JOB_NOT_FOUND"
    assert len(fake_supabase.tables["interview_kits"]) == kits_before
    assert queued == []


def test_create_interview_kit_rejects_a_match_of_another_person(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_supabase = FakeSupabase()
    _seed_premium_kit(fake_supabase)
    fake_supabase.tables["job_matches"].append(
        {"id": "match-2", "user_id": "user-2", "job_id": "job-9"}
    )
    kits_before = len(fake_supabase.tables["interview_kits"])
    queued = _create_kit_client(monkeypatch, fake_supabase)

    response = client.post(
        "/api/v1/interview-kits", json={"job_id": "job-1", "match_id": "match-2"}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "MATCH_NOT_FOUND"
    assert len(fake_supabase.tables["interview_kits"]) == kits_before
    assert queued == []


def test_create_interview_kit_accepts_own_job_and_match(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_supabase = FakeSupabase()
    _seed_premium_kit(fake_supabase)
    fake_supabase.tables["job_matches"].append(
        {"id": "match-1", "user_id": "user-1", "job_id": "job-1"}
    )
    queued = _create_kit_client(monkeypatch, fake_supabase)

    response = client.post(
        "/api/v1/interview-kits", json={"job_id": "job-1", "match_id": "match-1"}
    )

    assert response.status_code == 202
    assert len(queued) == 1


@pytest.mark.asyncio
async def test_interview_kit_task_does_not_read_a_job_of_another_person() -> None:
    fake_supabase = FakeSupabase()
    _seed_premium_kit(fake_supabase)
    fake_supabase.tables["job_descriptions"].append(
        {"id": "job-2", "user_id": "user-2", "job_title": "Puesto ajeno"}
    )
    fake_supabase.tables["interview_kits"][0]["job_id"] = "job-2"

    with pytest.raises(ValueError, match="job-2"):
        await analysis.run_interview_kit(
            "kit-1",
            "user-1",
            supabase=fake_supabase,
            gateway=FakeInterviewGateway(),  # type: ignore[arg-type]
        )

    assert fake_supabase.tables["interview_kits"][0]["status"] == "failed"
