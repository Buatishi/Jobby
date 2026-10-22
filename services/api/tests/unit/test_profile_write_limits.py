"""Largo máximo de los modelos de escritura del perfil (Decisión 28).

Las tablas guardan TEXT sin límite y esos textos terminan en los prompts de IA. El
parseo del CV no escribe por estos modelos (guarda con la clave de servicio), pero el
paso 3 del asistente reenvía por `SkillCreate` y `RejectedSkillCreate` las skills que
extrajo la IA: por eso los topes tienen que dejar pasar un CV real, por largo que sea.
"""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.models.profiles import (
    ACHIEVEMENT_MAX_LENGTH,
    ACHIEVEMENTS_MAX_ITEMS,
    FILENAME_MAX_LENGTH,
    LABEL_MAX_LENGTH,
    LONG_TEXT_MAX_LENGTH,
    NAME_MAX_LENGTH,
    NOTE_MAX_LENGTH,
    STORAGE_PATH_MAX_LENGTH,
    EducationCreate,
    ExperienceCreate,
    LanguageCreate,
    MasterProfileUpdate,
    RejectedSkillCreate,
    SkillCreate,
    UploadedDocumentCreate,
)
from app.services.cv_parser import PdfContent
from app.services.cv_parser.ai_structurer import (
    CVStructuredData,
    ParsedEducation,
    ParsedExperience,
    ParsedLanguage,
    ParsedSkill,
)
from app.tasks import parsing
from tests.fakes import FakeSupabase

# (modelo, campo, tope, datos válidos del resto del cuerpo, tabla, ruta)
FIELD_CASES: list[tuple[type[BaseModel], str, int, dict[str, Any], str, str]] = [
    (SkillCreate, "name", NAME_MAX_LENGTH, {}, "skills", "/profiles/skills"),
    (SkillCreate, "category", LABEL_MAX_LENGTH, {"name": "Python"}, "skills",
     "/profiles/skills"),
    (SkillCreate, "level", LABEL_MAX_LENGTH, {"name": "Python"}, "skills",
     "/profiles/skills"),
    (RejectedSkillCreate, "name", NAME_MAX_LENGTH, {}, "rejected_skills",
     "/profiles/rejected-skills"),
    (RejectedSkillCreate, "source", LABEL_MAX_LENGTH, {"name": "Excel"},
     "rejected_skills", "/profiles/rejected-skills"),
    (RejectedSkillCreate, "reason", NOTE_MAX_LENGTH, {"name": "Excel"},
     "rejected_skills", "/profiles/rejected-skills"),
    (ExperienceCreate, "company", NAME_MAX_LENGTH, {"title": "Dev"}, "experiences",
     "/profiles/experiences"),
    (ExperienceCreate, "title", NAME_MAX_LENGTH, {"company": "Acme"}, "experiences",
     "/profiles/experiences"),
    (ExperienceCreate, "description", LONG_TEXT_MAX_LENGTH,
     {"company": "Acme", "title": "Dev"}, "experiences", "/profiles/experiences"),
    (EducationCreate, "institution", NAME_MAX_LENGTH, {}, "educations",
     "/profiles/educations"),
    (EducationCreate, "field_of_study", NAME_MAX_LENGTH, {"institution": "UBA"},
     "educations", "/profiles/educations"),
    (EducationCreate, "degree_level", LABEL_MAX_LENGTH, {"institution": "UBA"},
     "educations", "/profiles/educations"),
    (LanguageCreate, "name", NAME_MAX_LENGTH, {}, "languages", "/profiles/languages"),
    (LanguageCreate, "level", LABEL_MAX_LENGTH, {"name": "Inglés"}, "languages",
     "/profiles/languages"),
]

DOCUMENT_BASE = {
    "profile_id": "profile-1",
    "type": "cv",
    "storage_path": "auth-user-1/cv.pdf",
    "original_filename": "cv.pdf",
    "mime_type": "application/pdf",
    "file_size": 1000,
}

DOCUMENT_CASES: list[tuple[str, int]] = [
    ("profile_id", 64),
    ("type", 32),
    ("storage_path", STORAGE_PATH_MAX_LENGTH),
    ("original_filename", FILENAME_MAX_LENGTH),
    ("mime_type", 255),
]


def _case_id(case: tuple[Any, ...]) -> str:
    model, field = case[0], case[1]
    return f"{model.__name__}.{field}"


def _setup() -> FakeSupabase:
    fake_supabase = FakeSupabase()

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    async def current_user() -> CurrentUser:
        return CurrentUser(
            id="user-1", supabase_uid="auth-user-1", email="person@example.com"
        )

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    return fake_supabase


# --- cada campo acepta justo el tope y rechaza uno más ---------------------------


@pytest.mark.parametrize("case", FIELD_CASES, ids=_case_id)
def test_text_fields_accept_exactly_the_limit_and_reject_one_more(
    case: tuple[type[BaseModel], str, int, dict[str, Any], str, str],
) -> None:
    model, field, limit, rest, _table, _route = case
    rest = {"name": "x", "company": "x", "title": "x", "institution": "x", **rest}
    rest = {key: value for key, value in rest.items() if key in model.model_fields}

    model.model_validate({**rest, field: "a" * limit})
    with pytest.raises(ValidationError):
        model.model_validate({**rest, field: "a" * (limit + 1)})


@pytest.mark.parametrize(("field", "limit"), DOCUMENT_CASES)
def test_document_fields_accept_exactly_the_limit_and_reject_one_more(
    field: str, limit: int
) -> None:
    UploadedDocumentCreate.model_validate({**DOCUMENT_BASE, field: "a" * limit})
    with pytest.raises(ValidationError):
        UploadedDocumentCreate.model_validate(
            {**DOCUMENT_BASE, field: "a" * (limit + 1)}
        )


def test_achievements_are_limited_in_count_and_in_length() -> None:
    base = {"company": "Acme", "title": "Dev"}

    at_the_limit = ["a" * ACHIEVEMENT_MAX_LENGTH] * ACHIEVEMENTS_MAX_ITEMS
    ExperienceCreate.model_validate({**base, "achievements": at_the_limit})
    with pytest.raises(ValidationError):
        ExperienceCreate.model_validate(
            {**base, "achievements": ["a"] * (ACHIEVEMENTS_MAX_ITEMS + 1)}
        )
    with pytest.raises(ValidationError):
        ExperienceCreate.model_validate(
            {**base, "achievements": ["a" * (ACHIEVEMENT_MAX_LENGTH + 1)]}
        )


def test_target_industry_items_are_limited_like_the_other_names() -> None:
    MasterProfileUpdate.model_validate({"target_industry": ["a" * NAME_MAX_LENGTH]})
    with pytest.raises(ValidationError):
        MasterProfileUpdate.model_validate(
            {"target_industry": ["a" * (NAME_MAX_LENGTH + 1)]}
        )


# --- por HTTP: 400 con el esquema de error y sin escribir nada ------------------


@pytest.mark.parametrize("case", FIELD_CASES, ids=_case_id)
def test_oversized_text_is_rejected_with_400_and_nothing_is_written(
    client: TestClient,
    case: tuple[type[BaseModel], str, int, dict[str, Any], str, str],
) -> None:
    model, field, limit, rest, table, route = case
    rest = {"name": "x", "company": "x", "title": "x", "institution": "x", **rest}
    rest = {key: value for key, value in rest.items() if key in model.model_fields}
    fake_supabase = _setup()

    response = client.post(
        f"/api/v1{route}", json={**rest, field: "a" * (limit + 1)}
    )

    assert response.status_code == 400
    body = response.json()
    assert set(body) == {"error", "code", "details"}
    assert body["code"] == "VALIDATION_ERROR"
    assert fake_supabase.tables[table] == []


@pytest.mark.parametrize(("field", "limit"), DOCUMENT_CASES)
def test_oversized_document_fields_are_rejected_with_400(
    client: TestClient, field: str, limit: int
) -> None:
    fake_supabase = _setup()

    response = client.post(
        "/api/v1/profiles/documents",
        json={**DOCUMENT_BASE, field: "a" * (limit + 1)},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert fake_supabase.tables["uploaded_documents"] == []


def test_the_profile_update_rejects_an_oversized_industry(
    client: TestClient,
) -> None:
    _setup()

    response = client.patch(
        "/api/v1/profiles/me",
        json={"target_industry": ["a" * (NAME_MAX_LENGTH + 1)]},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


# --- un CV real y largo no se rechaza -------------------------------------------


def _long_real_cv() -> CVStructuredData:
    """Lo que la IA devolvería para un CV de 20 páginas, con valores bien por encima de
    lo que se ve en la práctica."""
    detail = (
        "Lideré la migración de la plataforma de pagos a servicios independientes, con "
        "despliegues graduales, métricas de negocio y guardias rotativas. "
    )
    return CVStructuredData(
        skills=[
            ParsedSkill(
                name=f"Habilidad {index}: " + "gestión de proyectos con metodologías "
                "ágiles en equipos distribuidos".ljust(90),
                category="technical",
                level="advanced (uso profesional en producción)",
            )
            for index in range(150)
        ],
        experiences=[
            ParsedExperience(
                company="Empresa de Servicios Tecnológicos y Consultoría S.A.",
                title="Senior Software Engineer - Plataforma de Pagos (Remoto, LATAM)",
                description=(detail * 40)[:4_000],
                achievements=[(detail * 3)[:400] for _ in range(30)],
            )
            for _ in range(20)
        ],
        educations=[
            ParsedEducation(
                institution="Universidad Tecnológica Nacional, Facultad Regional",
                field_of_study="Ingeniería en Sistemas de Información con orientación "
                "en Ciencia de Datos",
                degree_level="bachelor",
            )
            for _ in range(6)
        ],
        languages=[
            ParsedLanguage(name="Inglés (certificado C1, uso diario)", level="advanced")
            for _ in range(8)
        ],
    )


def test_a_long_real_cv_fits_inside_the_write_limits() -> None:
    parsed = _long_real_cv()

    for skill in parsed.skills:
        SkillCreate.model_validate({**skill.model_dump(), "in_cv": True})
        RejectedSkillCreate.model_validate(skill.model_dump())
    for experience in parsed.experiences:
        ExperienceCreate.model_validate(experience.model_dump())
    for education in parsed.educations:
        EducationCreate.model_validate(education.model_dump())
    for language in parsed.languages:
        LanguageCreate.model_validate(language.model_dump())


@pytest.mark.asyncio
async def test_parsing_does_not_go_through_the_write_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El parseo guarda con la clave de servicio: un valor por encima del tope de la API
    no puede hacerlo fallar. Si alguien lo pasa por los modelos, esta prueba se pone en
    rojo en vez de dejar un CV sin procesar."""
    fake_supabase = FakeSupabase()
    fake_supabase.storage.files["user-1/cv.pdf"] = b"%PDF-1.4 fake"
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "document-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": "cv",
            "storage_path": "user-1/cv.pdf",
            "status": "pending",
        }
    )

    async def fake_extract_pdf_content(_path: Path) -> PdfContent:
        return PdfContent("Python", None)

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return CVStructuredData(
            skills=[
                ParsedSkill(
                    name="a" * (NAME_MAX_LENGTH * 5),
                    category="c" * (LABEL_MAX_LENGTH * 5),
                    level="advanced",
                )
            ],
            experiences=[
                ParsedExperience(
                    company="Acme",
                    title="Dev",
                    description="d" * (LONG_TEXT_MAX_LENGTH * 2),
                )
            ],
        )

    class FakeGateway:
        async def embed_many(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] * 1536 for _text in texts]

    monkeypatch.setattr(parsing, "extract_pdf_content", fake_extract_pdf_content)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)

    await parsing.run_parse_cv(
        "document-1",
        supabase=fake_supabase,
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    document = fake_supabase.tables["uploaded_documents"][0]
    assert document["status"] == "done"
    assert len(document["parsed_data"]["skills"][0]["name"]) == NAME_MAX_LENGTH * 5
    assert len(fake_supabase.tables["skills"]) == 1
