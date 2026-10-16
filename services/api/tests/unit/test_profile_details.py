"""Lo que la persona cargó a mano (experiencia, educación, idioma): leerlo y editarlo.

El paso 4 del asistente solo sabía crear: cada vez que se lo completaba se insertaba una
fila nueva (la misma experiencia dos o tres veces) y abría vacío. Ahora lee con
`GET /profiles/details` y edita con `PATCH /profiles/{tabla}/{id}`.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.models.profiles import (
    LABEL_MAX_LENGTH,
    NAME_MAX_LENGTH,
    EducationUpdate,
    ExperienceUpdate,
    LanguageUpdate,
)
from tests.fakes import FakeSupabase

EXPERIENCE_ID = "11111111-1111-4111-8111-111111111111"
OLDER_EXPERIENCE_ID = "11111111-1111-4111-8111-222222222222"
EDUCATION_ID = "22222222-2222-4222-8222-111111111111"
LANGUAGE_ID = "33333333-3333-4333-8333-111111111111"
OTHER_PERSON_EXPERIENCE_ID = "44444444-4444-4444-8444-111111111111"
UNKNOWN_ID = "99999999-9999-4999-8999-999999999999"


async def _current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1", supabase_uid="auth-user-1", email="person@example.com"
    )


def _world() -> FakeSupabase:
    supabase = FakeSupabase()
    supabase.tables["experiences"].extend(
        [
            {
                "id": OLDER_EXPERIENCE_ID,
                "profile_id": "profile-1",
                "company": "Initech",
                "title": "Soporte",
                "description": None,
                "created_at": "2026-01-01T10:00:00Z",
            },
            {
                "id": EXPERIENCE_ID,
                "profile_id": "profile-1",
                "company": "Acme",
                "title": "Backend Engineer",
                "description": "Construí la API de pagos.",
                "achievements": ["Bajé la latencia"],
                "created_at": "2026-03-01T10:00:00Z",
            },
            {
                "id": OTHER_PERSON_EXPERIENCE_ID,
                "profile_id": "profile-2",
                "company": "Globex",
                "title": "Cargo ajeno",
                "description": "DATO-AJENO",
                "created_at": "2026-04-01T10:00:00Z",
            },
        ]
    )
    supabase.tables["educations"].append(
        {
            "id": EDUCATION_ID,
            "profile_id": "profile-1",
            "institution": "UTN",
            "field_of_study": "Sistemas",
            "degree_level": "bachelor",
            "embedding": [0.1, 0.2],
            "created_at": "2026-02-01T10:00:00Z",
        }
    )
    supabase.tables["languages"].append(
        {
            "id": LANGUAGE_ID,
            "profile_id": "profile-1",
            "name": "Inglés",
            "proficiency": "professional",
            "created_at": "2026-02-01T10:00:00Z",
        }
    )
    return supabase


@pytest.fixture()
def supabase() -> FakeSupabase:
    fake = _world()

    async def fake_client() -> FakeSupabase:
        return fake

    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    return fake


def _row(supabase: FakeSupabase, table: str, row_id: str) -> dict[str, Any]:
    return next(row for row in supabase.tables[table] if row["id"] == row_id)


def test_details_list_the_own_rows_newest_first(
    client: TestClient, supabase: FakeSupabase
) -> None:
    response = client.get("/api/v1/profiles/details")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["experiences"]] == [
        EXPERIENCE_ID,
        OLDER_EXPERIENCE_ID,
    ]
    assert body["experiences"][0] == {
        "id": EXPERIENCE_ID,
        "company": "Acme",
        "title": "Backend Engineer",
        "description": "Construí la API de pagos.",
    }
    assert body["educations"] == [
        {
            "id": EDUCATION_ID,
            "institution": "UTN",
            "field_of_study": "Sistemas",
            "degree_level": "bachelor",
        }
    ]
    # La columna se llama proficiency; la web la conoce como level.
    assert body["languages"] == [
        {"id": LANGUAGE_ID, "name": "Inglés", "level": "professional"}
    ]


def test_details_never_include_another_person_or_the_vectors(
    client: TestClient, supabase: FakeSupabase
) -> None:
    response = client.get("/api/v1/profiles/details")

    assert "DATO-AJENO" not in response.text
    assert OTHER_PERSON_EXPERIENCE_ID not in response.text
    assert "embedding" not in response.text


def test_details_of_an_empty_profile_are_empty_lists(client: TestClient) -> None:
    fake = FakeSupabase()

    async def fake_client() -> FakeSupabase:
        return fake

    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.get("/api/v1/profiles/details")

    assert response.status_code == 200
    assert response.json() == {"experiences": [], "educations": [], "languages": []}


def test_updating_an_experience_keeps_what_was_not_sent(
    client: TestClient, supabase: FakeSupabase
) -> None:
    response = client.patch(
        f"/api/v1/profiles/experiences/{EXPERIENCE_ID}",
        json={"company": "Acme SA", "title": "Senior Backend Engineer"},
    )

    assert response.status_code == 200
    assert response.json()["company"] == "Acme SA"
    stored = _row(supabase, "experiences", EXPERIENCE_ID)
    assert stored["company"] == "Acme SA"
    assert stored["title"] == "Senior Backend Engineer"
    assert stored["description"] == "Construí la API de pagos."
    assert stored["achievements"] == ["Bajé la latencia"]
    # No se creó otra fila: editar no duplica.
    assert len(supabase.tables["experiences"]) == 3


def test_a_null_does_not_empty_a_required_column(
    client: TestClient, supabase: FakeSupabase
) -> None:
    response = client.patch(
        f"/api/v1/profiles/experiences/{EXPERIENCE_ID}",
        json={"company": None, "description": None},
    )

    assert response.status_code == 200
    stored = _row(supabase, "experiences", EXPERIENCE_ID)
    assert stored["company"] == "Acme"
    # Una columna que admite null sí se puede vaciar.
    assert stored["description"] is None


def test_an_empty_body_changes_nothing_and_still_answers(
    client: TestClient, supabase: FakeSupabase
) -> None:
    response = client.patch(f"/api/v1/profiles/educations/{EDUCATION_ID}", json={})

    assert response.status_code == 200
    assert response.json()["institution"] == "UTN"
    assert _row(supabase, "educations", EDUCATION_ID)["field_of_study"] == "Sistemas"


def test_updating_an_education_does_not_return_its_vector(
    client: TestClient, supabase: FakeSupabase
) -> None:
    response = client.patch(
        f"/api/v1/profiles/educations/{EDUCATION_ID}",
        json={"institution": "UBA"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": EDUCATION_ID,
        "institution": "UBA",
        "field_of_study": "Sistemas",
        "degree_level": "bachelor",
    }


def test_the_language_level_is_stored_as_proficiency(
    client: TestClient, supabase: FakeSupabase
) -> None:
    response = client.patch(
        f"/api/v1/profiles/languages/{LANGUAGE_ID}",
        json={"name": "Inglés", "level": "advanced"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": LANGUAGE_ID,
        "name": "Inglés",
        "level": "advanced",
    }
    stored = _row(supabase, "languages", LANGUAGE_ID)
    assert stored["proficiency"] == "advanced"
    assert "level" not in stored


def test_the_row_of_another_person_is_not_found_and_not_changed(
    client: TestClient, supabase: FakeSupabase
) -> None:
    response = client.patch(
        f"/api/v1/profiles/experiences/{OTHER_PERSON_EXPERIENCE_ID}",
        json={"company": "Mía ahora"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "EXPERIENCE_NOT_FOUND"
    assert "DATO-AJENO" not in response.text
    stored = _row(supabase, "experiences", OTHER_PERSON_EXPERIENCE_ID)
    assert stored["company"] == "Globex"


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("experiences", "EXPERIENCE_NOT_FOUND"),
        ("educations", "EDUCATION_NOT_FOUND"),
        ("languages", "LANGUAGE_NOT_FOUND"),
    ],
)
def test_an_unknown_row_is_a_404_with_the_error_shape(
    client: TestClient, supabase: FakeSupabase, path: str, code: str
) -> None:
    response = client.patch(f"/api/v1/profiles/{path}/{UNKNOWN_ID}", json={})

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == code
    assert set(body) == {"error", "code", "details"}


def test_a_malformed_id_is_a_validation_error(
    client: TestClient, supabase: FakeSupabase
) -> None:
    response = client.patch("/api/v1/profiles/languages/no-es-uuid", json={})

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("path", "row_id", "body"),
    [
        ("experiences", EXPERIENCE_ID, {"title": "x" * (NAME_MAX_LENGTH + 1)}),
        ("educations", EDUCATION_ID, {"degree_level": "x" * (LABEL_MAX_LENGTH + 1)}),
        ("languages", LANGUAGE_ID, {"name": "x" * (NAME_MAX_LENGTH + 1)}),
    ],
)
def test_updates_keep_the_length_limits_of_the_create_models(
    client: TestClient,
    supabase: FakeSupabase,
    path: str,
    row_id: str,
    body: dict[str, Any],
) -> None:
    before = [dict(row) for row in supabase.tables[path]]

    response = client.patch(f"/api/v1/profiles/{path}/{row_id}", json=body)

    assert response.status_code == 400
    assert supabase.tables[path] == before


def test_an_update_recalculates_the_stored_percentage(
    client: TestClient, supabase: FakeSupabase
) -> None:
    supabase.tables["master_profiles"][0]["completeness_pct"] = 99

    response = client.patch(
        f"/api/v1/profiles/languages/{LANGUAGE_ID}", json={"level": "native"}
    )

    assert response.status_code == 200
    assert supabase.tables["master_profiles"][0]["completeness_pct"] != 99


def test_update_payloads_only_carry_what_was_sent() -> None:
    assert ExperienceUpdate().to_update_payload() == {}
    assert ExperienceUpdate(title="Dev").to_update_payload() == {"title": "Dev"}
    assert EducationUpdate(institution=None).to_update_payload() == {}
    assert LanguageUpdate(level="basic").to_update_payload() == {
        "proficiency": "basic"
    }
