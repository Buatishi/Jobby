import pytest
from fastapi.testclient import TestClient

from app.core.public_errors import GENERIC_TASK_ERROR, public_error_message
from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.ai_gateway.errors import (
    PremiumRequiredError,
    ProviderUnavailableError,
)
from app.services.cv_parser.errors import CVParsingError
from app.services.scraper.playwright_scraper import ScraperBlockedError
from app.services.scraper.url_guard import UnsafeUrlError
from tests.fakes import FakeSupabase


async def _user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


def _use(fake_supabase: FakeSupabase) -> None:
    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_supabase_client] = fake_client


# --- análisis de puestos: la URL no puede apuntar a la red interna -----------


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost:8000/api/v1/health",
        "http://10.0.0.5/admin",
        "file:///etc/passwd",
        "https://user:secret@example.com/job",
    ],
)
def test_analyze_job_rejects_urls_to_internal_destinations(
    client: TestClient,
    url: str,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["master_profiles"][0]["completeness_pct"] = 80
    _use(fake_supabase)

    response = client.post("/api/v1/jobs/analyze", json={"source": "url", "url": url})

    assert response.status_code == 400
    assert response.json()["code"] == "JOB_URL_INVALID"


def test_analyze_job_rejects_oversized_text(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["master_profiles"][0]["completeness_pct"] = 80
    _use(fake_supabase)

    response = client.post(
        "/api/v1/jobs/analyze",
        json={"source": "text", "raw_text": "a" * 30_001},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


# --- kits: las URLs deben ser de LinkedIn y públicas --------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"company_linkedin_url": "https://evil.example.com/steal"},
        {"interviewer_linkedin_url": "http://169.254.169.254/latest/meta-data/"},
        {"company_linkedin_url": "https://linkedin.com.evil.com/company/acme"},
        {"interviewer_linkedin_url": "https://linkedin.com@10.0.0.1/"},
    ],
)
def test_create_kit_rejects_urls_that_are_not_public_linkedin(
    client: TestClient,
    payload: dict[str, str],
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["users"][0]["tier"] = "premium"
    fake_supabase.tables["master_profiles"][0]["completeness_pct"] = 100
    _use(fake_supabase)

    response = client.post(
        "/api/v1/interview-kits",
        json={"job_id": "job-1", **payload},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "LINKEDIN_URL_INVALID"


# --- mensajes de error hacia el usuario: sin detalles internos ----------------


def test_public_errors_never_expose_internal_details() -> None:
    internal = ProviderUnavailableError(
        "openai",
        "OpenAI rechazo la API key configurada. Revisa OPENAI_API_KEY en Render.",
    )

    message = public_error_message(internal)

    assert "OPENAI_API_KEY" not in message
    assert "Render" not in message
    assert message.startswith("El servicio de IA no está disponible")


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (
            PremiumRequiredError("ats_optimize"),
            "Esta función requiere el plan premium.",
        ),
        (
            UnsafeUrlError("host interno 10.0.0.1"),
            "La URL indicada no es válida o no está permitida.",
        ),
        (
            ScraperBlockedError("cloudflare"),
            "No pudimos leer la página indicada. "
            "Pegá el texto del puesto para continuar.",
        ),
        (
            CVParsingError("pdf ilegible en /tmp/xyz.pdf"),
            "No pudimos leer tu CV. Verificá que sea un PDF con texto seleccionable.",
        ),
        (RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing"), GENERIC_TASK_ERROR),
        (None, GENERIC_TASK_ERROR),
    ],
)
def test_public_error_message_maps_known_failures(
    exc: BaseException | None,
    expected: str,
) -> None:
    assert public_error_message(exc) == expected
