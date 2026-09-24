"""Los recursos inexistentes responden 404 con el formato único de error.

Regresión del error reproducido el 2026-09-21 contra el cliente real de Supabase: con
`single()`, PostgREST devuelve 406 (PGRST116) cuando no hay filas y el cliente lo lanza
como excepción, así que el endpoint nunca llegaba a su propio 404 y la API terminaba
respondiendo 500 en texto plano. El simulador de `tests/fakes.py` ahora se comporta
igual que el cliente real, así que estos tests fallan si alguien vuelve a usar
`single()` para una búsqueda que puede no encontrar nada.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.core.errors import supabase_error_handler
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


@pytest.fixture()
def fake_supabase() -> Iterator[FakeSupabase]:
    supabase = FakeSupabase()

    async def fake_client() -> FakeSupabase:
        return supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    yield supabase
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("method", "path", "code"),
    [
        ("get", "/api/v1/matches/no-existe", "MATCH_NOT_FOUND"),
        # El id del puesto se valida como uuid: uno mal formado ya es un 400.
        ("get", "/api/v1/jobs/00000000-0000-4000-8000-000000000000", "JOB_NOT_FOUND"),
        ("get", "/api/v1/ats/no-existe", "JOB_NOT_FOUND"),
        ("get", "/api/v1/interview-kits/no-existe", "INTERVIEW_KIT_NOT_FOUND"),
        ("delete", "/api/v1/profiles/documents/no-existe", "DOCUMENT_NOT_FOUND"),
    ],
)
def test_unknown_resource_returns_404_with_error_format(
    client: TestClient,
    fake_supabase: FakeSupabase,
    method: str,
    path: str,
    code: str,
) -> None:
    response = getattr(client, method)(path)

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["code"] == code
    assert set(body) == {"error", "code", "details"}


def test_match_report_is_found_by_job_id(
    client: TestClient,
    fake_supabase: FakeSupabase,
) -> None:
    """La web pide el reporte con el id del puesto, no con el del match."""
    fake_supabase.tables["job_descriptions"].append(
        {
            "id": "job-1",
            "user_id": "user-1",
            "job_title": "Backend",
            "company_name": "Acme",
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
            "recommendations": [],
            "user_rating": None,
            "ai_model_used": "deepseek-chat",
        }
    )

    response = client.get("/api/v1/matches/job-1")

    assert response.status_code == 200
    assert response.json()["id"] == "match-1"


async def test_fake_single_fails_and_maybe_single_returns_none() -> None:
    """El simulador replica al cliente real: esa diferencia fue la que tapó el error."""
    supabase = FakeSupabase()

    query = supabase.table("job_matches").select("*").eq("id", "x")
    empty = await query.maybe_single().execute()
    assert empty is None

    with pytest.raises(APIError) as error:
        await supabase.table("job_matches").select("*").eq("id", "x").single().execute()
    assert error.value.code == "PGRST116"


async def test_supabase_error_handler_keeps_the_error_format() -> None:
    """Si un error del cliente llega sin manejar, la respuesta sigue siendo JSON."""

    class _Request:
        url = type("Url", (), {"path": "/api/v1/matches/x"})()

    response = await supabase_error_handler(
        _Request(),  # type: ignore[arg-type]
        APIError({"message": "boom", "code": "PGRST500", "hint": None, "details": ""}),
    )

    assert response.status_code == 500
    assert response.media_type == "application/json"


def test_unknown_route_still_returns_the_error_format(client: TestClient) -> None:
    response = client.get("/api/v1/ruta-que-no-existe")

    assert response.status_code == 404
    body: dict[str, Any] = response.json()
    assert set(body) == {"error", "code", "details"}
