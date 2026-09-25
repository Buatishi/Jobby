"""Los casos de integración de la consigna (3.7), contra la base de pruebas real.

POST 201, GET 200, PATCH, DELETE, 400, 404 y una regla de negocio. Cada prueba usa su
propia persona, creada y borrada por `create_person`, así que no dependen del orden.
"""

import uuid
from typing import Any

import httpx
import pytest
from supabase import AsyncClient

from app.models.auth import CurrentUser
from tests.integration.conftest import CreatePerson

pytestmark = pytest.mark.integration


async def _profile_id(database: AsyncClient, user_id: str) -> str:
    row = (
        await database.table("master_profiles")
        .select("id")
        .eq("user_id", user_id)
        .single()
        .execute()
    ).data
    return str(row["id"])


async def _insert_job(database: AsyncClient, user_id: str) -> str:
    """Un puesto como lo guarda el análisis, sin llamar a la IA."""
    rows = (
        await database.table("job_descriptions")
        .insert(
            {
                "user_id": user_id,
                "raw_text": "Buscamos backend con Python y FastAPI",
                "job_title": "Backend Engineer",
                "company_name": "Acme",
                "salary_min": 1000,
                "salary_max": 2000,
                "currency": "USD",
            }
        )
        .execute()
    ).data
    return str(rows[0]["id"])


async def _job_row(database: AsyncClient, job_id: str) -> dict[str, Any] | None:
    rows = (
        await database.table("job_descriptions").select("*").eq("id", job_id).execute()
    ).data
    return rows[0] if rows else None


async def test_post_creates_a_skill_and_answers_201(
    api: httpx.AsyncClient, database: AsyncClient, person: CurrentUser
) -> None:
    response = await api.post(
        "/api/v1/profiles/skills", json={"name": "Python", "confirmed": True}
    )

    assert response.status_code == 201
    profile_id = await _profile_id(database, person.id)
    stored = (
        await database.table("skills")
        .select("name,confirmed")
        .eq("profile_id", profile_id)
        .execute()
    ).data
    assert stored == [{"name": "Python", "confirmed": True}]


async def test_get_lists_and_reads_the_saved_job(
    api: httpx.AsyncClient, database: AsyncClient, person: CurrentUser
) -> None:
    job_id = await _insert_job(database, person.id)

    listed = await api.get("/api/v1/jobs")
    read = await api.get(f"/api/v1/jobs/{job_id}")

    assert listed.status_code == 200
    assert [job["id"] for job in listed.json()] == [job_id]
    assert read.status_code == 200
    assert read.json()["job_title"] == "Backend Engineer"


async def test_patch_updates_only_the_fields_sent(
    api: httpx.AsyncClient, database: AsyncClient, person: CurrentUser
) -> None:
    job_id = await _insert_job(database, person.id)

    response = await api.patch(
        f"/api/v1/jobs/{job_id}",
        json={"job_title": "Backend Sr", "required_seniority": "senior"},
    )

    assert response.status_code == 200
    stored = await _job_row(database, job_id)
    assert stored is not None
    assert stored["job_title"] == "Backend Sr"
    assert stored["required_seniority"] == "senior"
    assert stored["company_name"] == "Acme"
    assert stored["raw_text"] == "Buscamos backend con Python y FastAPI"


async def test_delete_removes_the_job_and_answers_204(
    api: httpx.AsyncClient, database: AsyncClient, person: CurrentUser
) -> None:
    job_id = await _insert_job(database, person.id)

    response = await api.delete(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 204
    assert await _job_row(database, job_id) is None


async def test_delete_of_a_job_with_a_match_is_409_and_keeps_both(
    api: httpx.AsyncClient, database: AsyncClient, person: CurrentUser
) -> None:
    """Sin el 409, la clave foránea borraría la comparación en cascada."""
    job_id = await _insert_job(database, person.id)
    match = (
        await database.table("job_matches")
        .insert(
            {
                "user_id": person.id,
                "profile_id": await _profile_id(database, person.id),
                "job_id": job_id,
                "match_score": 70,
            }
        )
        .execute()
    ).data[0]

    response = await api.delete(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 409
    assert response.json()["code"] == "JOB_HAS_DEPENDENT_RESULTS"
    assert await _job_row(database, job_id) is not None
    kept = (
        await database.table("job_matches").select("id").eq("id", match["id"]).execute()
    ).data
    assert kept == [{"id": match["id"]}]


async def test_invalid_data_is_400_and_changes_nothing(
    api: httpx.AsyncClient, database: AsyncClient, person: CurrentUser
) -> None:
    job_id = await _insert_job(database, person.id)

    response = await api.patch(
        f"/api/v1/jobs/{job_id}", json={"required_seniority": "semi senior"}
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    stored = await _job_row(database, job_id)
    assert stored is not None
    assert stored["required_seniority"] is None


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/jobs/no-es-un-uuid",
        "/api/v1/matches/no-es-un-uuid",
        "/api/v1/interview-kits/no-es-un-uuid",
        "/api/v1/ats/no-es-un-uuid",
    ],
)
async def test_a_malformed_id_is_400_with_the_real_database(
    api: httpx.AsyncClient, path: str
) -> None:
    response = await api.get(path)

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


async def test_a_missing_or_foreign_job_is_404(
    api: httpx.AsyncClient, database: AsyncClient, create_person: CreatePerson
) -> None:
    stranger = await create_person()
    foreign_job_id = await _insert_job(database, stranger.id)

    for job_id in (str(uuid.uuid4()), foreign_job_id):
        response = await api.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 404
        assert response.json()["code"] == "JOB_NOT_FOUND"

    response = await api.delete(f"/api/v1/jobs/{foreign_job_id}")
    assert response.status_code == 404
    assert await _job_row(database, foreign_job_id) is not None


async def test_a_profile_below_60_percent_cannot_analyze_jobs(
    api: httpx.AsyncClient,
) -> None:
    """Regla de negocio: un perfil nuevo no llega al 60 % que pide el análisis."""
    response = await api.post(
        "/api/v1/jobs/analyze",
        json={"source": "text", "raw_text": "Buscamos backend con Python"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "PROFILE_INCOMPLETE"
