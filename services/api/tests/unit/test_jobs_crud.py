"""Edición y borrado de puestos (Decisión 1): PATCH y DELETE de /jobs/{job_id}."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from tests.fakes import FakeSupabase

JOB_ID = "3f1c2a4e-8b7d-4c21-9e5a-1d2f3a4b5c6d"
OTHER_USER_JOB_ID = "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d"
MISSING_JOB_ID = "00000000-0000-4000-8000-000000000000"


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


@pytest.fixture()
def fake_supabase() -> Iterator[FakeSupabase]:
    supabase = FakeSupabase()
    supabase.tables["job_descriptions"].extend(
        [
            {
                "id": JOB_ID,
                "user_id": "user-1",
                "source_url": None,
                "raw_text": "Buscamos backend con Python",
                "job_title": "Backend Engineer",
                "company_name": "Acme",
                "required_seniority": "Semi Senior",
                "required_modality": "remote",
                "salary_min": 1000,
                "salary_max": 2000,
                "currency": "USD",
            },
            {
                "id": OTHER_USER_JOB_ID,
                "user_id": "user-2",
                "raw_text": "Puesto de otra persona",
                "job_title": "Data Engineer",
                "company_name": "Globex",
            },
        ]
    )

    async def fake_client() -> FakeSupabase:
        return supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    yield supabase
    app.dependency_overrides.clear()


def _job(supabase: FakeSupabase, job_id: str) -> dict[str, Any] | None:
    for row in supabase.tables["job_descriptions"]:
        if row["id"] == job_id:
            return row
    return None


def _assert_error(response: Any, status_code: int, code: str) -> dict[str, Any]:
    assert response.status_code == status_code
    body: dict[str, Any] = response.json()
    assert body["code"] == code
    assert set(body) == {"error", "code", "details"}
    return body


def test_patch_changes_only_the_fields_sent(
    client: TestClient, fake_supabase: FakeSupabase
) -> None:
    response = client.patch(
        f"/api/v1/jobs/{JOB_ID}",
        json={
            "job_title": "  Backend Engineer Sr  ",
            "required_seniority": "senior",
            "salary_max": 2500,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job_title"] == "Backend Engineer Sr"
    assert body["required_seniority"] == "senior"
    assert body["salary_max"] == 2500
    stored = _job(fake_supabase, JOB_ID)
    assert stored is not None
    assert stored["company_name"] == "Acme"
    assert stored["required_modality"] == "remote"
    assert stored["raw_text"] == "Buscamos backend con Python"


def test_patch_with_null_clears_the_field(
    client: TestClient, fake_supabase: FakeSupabase
) -> None:
    response = client.patch(
        f"/api/v1/jobs/{JOB_ID}", json={"company_name": None, "salary_min": None}
    )

    assert response.status_code == 200
    stored = _job(fake_supabase, JOB_ID)
    assert stored is not None
    assert stored["company_name"] is None
    assert stored["salary_min"] is None
    assert stored["salary_max"] == 2000


@pytest.mark.parametrize(
    "payload",
    [
        {"raw_text": "Otro texto"},
        {"source_url": "https://empresa.com/otro"},
        {"user_id": "user-2"},
        {"embedding": [0.1]},
    ],
)
def test_patch_rejects_fields_that_are_not_editable(
    client: TestClient, fake_supabase: FakeSupabase, payload: dict[str, Any]
) -> None:
    before = dict(_job(fake_supabase, JOB_ID) or {})

    response = client.patch(f"/api/v1/jobs/{JOB_ID}", json=payload)

    _assert_error(response, 400, "VALIDATION_ERROR")
    assert _job(fake_supabase, JOB_ID) == before


@pytest.mark.parametrize(
    "payload",
    [
        {"required_seniority": "Semi Senior"},
        {"required_modality": "remoto"},
        {"currency": "usd"},
        {"salary_min": -1},
        {"job_title": "   "},
        {"job_title": "x" * 201},
    ],
)
def test_patch_validates_each_value(
    client: TestClient, fake_supabase: FakeSupabase, payload: dict[str, Any]
) -> None:
    response = client.patch(f"/api/v1/jobs/{JOB_ID}", json=payload)

    _assert_error(response, 400, "VALIDATION_ERROR")


def test_patch_without_fields_is_rejected(
    client: TestClient, fake_supabase: FakeSupabase
) -> None:
    response = client.patch(f"/api/v1/jobs/{JOB_ID}", json={})

    _assert_error(response, 400, "JOB_UPDATE_EMPTY")


def test_patch_rejects_a_minimum_salary_above_the_stored_maximum(
    client: TestClient, fake_supabase: FakeSupabase
) -> None:
    response = client.patch(f"/api/v1/jobs/{JOB_ID}", json={"salary_min": 3000})

    body = _assert_error(response, 400, "JOB_SALARY_RANGE_INVALID")
    assert body["details"] == {"salary_min": 3000, "salary_max": 2000}
    stored = _job(fake_supabase, JOB_ID)
    assert stored is not None
    assert stored["salary_min"] == 1000


def test_a_bad_stored_salary_range_does_not_block_other_edits(
    client: TestClient, fake_supabase: FakeSupabase
) -> None:
    stored = _job(fake_supabase, JOB_ID)
    assert stored is not None
    stored.update({"salary_min": 5000, "salary_max": 3000})

    response = client.patch(f"/api/v1/jobs/{JOB_ID}", json={"job_title": "Backend"})

    assert response.status_code == 200
    assert response.json()["job_title"] == "Backend"


@pytest.mark.parametrize("job_id", [OTHER_USER_JOB_ID, MISSING_JOB_ID])
def test_patch_of_a_job_that_is_not_yours_returns_404(
    client: TestClient, fake_supabase: FakeSupabase, job_id: str
) -> None:
    response = client.patch(f"/api/v1/jobs/{job_id}", json={"job_title": "Mío"})

    _assert_error(response, 404, "JOB_NOT_FOUND")
    other = _job(fake_supabase, OTHER_USER_JOB_ID)
    assert other is not None
    assert other["job_title"] == "Data Engineer"


def test_delete_removes_a_job_without_results(
    client: TestClient, fake_supabase: FakeSupabase
) -> None:
    response = client.delete(f"/api/v1/jobs/{JOB_ID}")

    assert response.status_code == 204
    assert response.content == b""
    assert _job(fake_supabase, JOB_ID) is None
    assert _job(fake_supabase, OTHER_USER_JOB_ID) is not None


@pytest.mark.parametrize(
    ("table", "expected_details"),
    [
        ("job_matches", {"has_matches": True, "has_interview_kits": False}),
        ("interview_kits", {"has_matches": False, "has_interview_kits": True}),
    ],
)
def test_delete_is_refused_when_the_job_has_results(
    client: TestClient,
    fake_supabase: FakeSupabase,
    table: str,
    expected_details: dict[str, bool],
) -> None:
    fake_supabase.tables[table].append(
        {"id": f"{table}-1", "user_id": "user-1", "job_id": JOB_ID}
    )

    response = client.delete(f"/api/v1/jobs/{JOB_ID}")

    body = _assert_error(response, 409, "JOB_HAS_DEPENDENT_RESULTS")
    assert body["details"] == expected_details
    assert _job(fake_supabase, JOB_ID) is not None
    assert len(fake_supabase.tables[table]) == 1


@pytest.mark.parametrize("job_id", [OTHER_USER_JOB_ID, MISSING_JOB_ID])
def test_delete_of_a_job_that_is_not_yours_returns_404(
    client: TestClient, fake_supabase: FakeSupabase, job_id: str
) -> None:
    response = client.delete(f"/api/v1/jobs/{job_id}")

    _assert_error(response, 404, "JOB_NOT_FOUND")
    assert _job(fake_supabase, OTHER_USER_JOB_ID) is not None


@pytest.mark.parametrize(
    ("method", "kwargs"),
    [
        ("get", {}),
        ("patch", {"json": {"job_title": "Backend"}}),
        ("delete", {}),
    ],
)
def test_a_malformed_job_id_is_a_400_not_a_database_error(
    client: TestClient,
    fake_supabase: FakeSupabase,
    method: str,
    kwargs: dict[str, Any],
) -> None:
    """PostgreSQL rechaza un uuid mal formado y la API respondía 500; ahora, 400."""
    response = getattr(client, method)("/api/v1/jobs/no-es-un-uuid", **kwargs)

    _assert_error(response, 400, "VALIDATION_ERROR")


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_editing_or_deleting_requires_a_session(
    client: TestClient, method: str
) -> None:
    kwargs: dict[str, Any] = {}
    if method == "patch":
        kwargs["json"] = {"job_title": "Backend"}

    response = getattr(client, method)(f"/api/v1/jobs/{JOB_ID}", **kwargs)

    _assert_error(response, 401, "UNAUTHORIZED")
