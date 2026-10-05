"""CV descargable: encabezado leído del CV y contenido del perfil confirmado."""

from typing import Any

from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.cv_parser.ai_structurer import (
    CVStructuredData,
    _normalize_structured_payload,
)
from app.services.cv_parser.merge_logic import merge_structured_cv_data
from app.services.printable_cv import build_printable_cv
from tests.fakes import FakeSupabase

PARSED_DATA: dict[str, Any] = {
    "contact": {
        "full_name": "Lucía Ferreyra",
        "email": "lucia.demo@example.com",
        "phone": "",
        "location": "Buenos Aires",
        "linkedin_url": "",
    },
    "skills": [{"name": "Python"}, {"name": "SQL"}],
    "experiences": [
        {
            "company": "Distribuidora Andina",
            "title": "Pasante de datos",
            "achievements": [],
        }
    ],
    "educations": [
        {"institution": "Escuela Técnica", "field_of_study": "Programación"}
    ],
    "languages": [{"name": "Inglés", "level": "unknown"}],
    "certifications": [{"name": "Análisis de Datos con Python", "issuer": ""}],
}


def test_the_parser_keeps_the_contact_with_its_usual_aliases() -> None:
    normalized = _normalize_structured_payload(
        {"contact": {"name": "Lucía Ferreyra", "mail": "lucia.demo@example.com"}}
    )

    assert normalized["contact"]["full_name"] == "Lucía Ferreyra"
    assert normalized["contact"]["email"] == "lucia.demo@example.com"
    assert normalized["contact"]["phone"] == ""


def test_a_cv_without_contact_still_validates_and_is_stored_empty() -> None:
    data = CVStructuredData.model_validate(
        _normalize_structured_payload({"skills": []})
    )

    stored = merge_structured_cv_data(data, [])

    assert stored["contact"] == {
        "full_name": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin_url": "",
    }


def _build(**overrides: Any) -> Any:
    arguments: dict[str, Any] = {
        "profile": {"headline": "Analista de datos", "linkedin_url": None},
        "primary_cv": {"parsed_data": PARSED_DATA},
        "account_email": "cuenta@example.com",
        "skills": [],
        "experiences": [],
        "educations": [],
        "languages": [],
        "certifications": [],
    }
    arguments.update(overrides)
    return build_printable_cv(**arguments)


def test_empty_profile_sections_fall_back_to_what_the_cv_says() -> None:
    cv = _build()

    assert cv.contact.full_name == "Lucía Ferreyra"
    assert cv.skills == ["Python", "SQL"]
    assert cv.experiences[0].title == "Pasante de datos"
    assert cv.certifications[0].name == "Análisis de Datos con Python"
    # «unknown» es el nivel que pone el lector cuando no figura: no se imprime.
    assert cv.languages[0].level is None


def test_the_confirmed_profile_wins_over_the_cv_text() -> None:
    cv = _build(
        skills=[{"name": "Python"}, {"name": "python"}, {"name": "Looker Studio"}],
        languages=[{"name": "Inglés", "proficiency": "intermediate"}],
        experiences=[
            {"company": "A", "title": "Antes", "started_at": "2025-01-01"},
            {"company": "B", "title": "Después", "started_at": "2026-03-01"},
            {"company": "C", "title": "Sin fecha"},
        ],
    )

    assert cv.skills == ["Python", "Looker Studio"]
    assert cv.languages[0].level == "intermediate"
    assert [item.title for item in cv.experiences] == ["Después", "Antes", "Sin fecha"]


def test_the_header_falls_back_to_the_account_and_the_profile() -> None:
    cv = _build(
        profile={"headline": None, "linkedin_url": "https://linkedin.com/in/demo"},
        primary_cv=None,
    )

    assert cv.contact.full_name == ""
    assert cv.contact.email == "cuenta@example.com"
    assert cv.contact.linkedin_url == "https://linkedin.com/in/demo"


async def _current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1", supabase_uid="auth-user-1", email="person@example.com"
    )


def test_the_endpoint_returns_only_the_callers_profile(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "doc-1",
            "user_id": "user-1",
            "type": "cv",
            "is_primary": True,
            "parsed_data": PARSED_DATA,
        }
    )
    fake_supabase.tables["skills"].extend(
        [
            {"profile_id": "profile-1", "name": "Python"},
            {"profile_id": "profile-2", "name": "Kubernetes"},
        ]
    )

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.get("/api/v1/profiles/cv")

    assert response.status_code == 200
    body = response.json()
    assert body["contact"]["full_name"] == "Lucía Ferreyra"
    assert body["headline"] == "Backend Engineer"
    assert body["skills"] == ["Python"]
