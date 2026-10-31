"""El CV descargable con el nombre de la persona y sin cursos repetidos.

Dos fallas medidas en la cuenta del autor el 2026-10-31:

- El lector de CV dejó de guardar el contacto en `parsed_data` (la Decisión 26 dice que
  sí): el PDF salía con «Tu nombre» y sin teléfono ni ciudad.
- El lector lista un mismo curso como estudio y como certificado, y el PDF lo imprimía
  dos veces: seis renglones de más que lo pasaban de una hoja.
"""

from typing import Any

import pytest

from app.services.cv_parser import PdfContent
from app.services.cv_parser.ai_structurer import (
    CVStructuredData,
    ParsedContact,
    ParsedSkill,
)
from app.services.printable_cv import build_printable_cv
from app.tasks import parsing
from tests.fakes import FakeSupabase


def _build(
    *,
    educations: list[dict[str, Any]] | None = None,
    certifications: list[dict[str, Any]] | None = None,
) -> Any:
    parsed = {
        "educations": educations or [],
        "certifications": certifications or [],
    }
    return build_printable_cv(
        profile={},
        primary_cv={"parsed_data": parsed},
        account_email="persona@example.com",
        skills=[],
        experiences=[],
        educations=[],
        languages=[],
        certifications=[],
    )


def _education(institution: str, title: str, **extra: Any) -> dict[str, Any]:
    return {
        "institution": institution,
        "field_of_study": title,
        "degree_level": "",
        **extra,
    }


# --- cursos repetidos ------------------------------------------------------------


def test_a_course_listed_as_study_and_certificate_prints_once() -> None:
    cv = _build(
        educations=[
            _education(
                "Coursera IBM",
                "Excel Basics for Data Analysis",
                started_at="2025-04",
                ended_at="2025-03",
            )
        ],
        certifications=[
            {
                "name": "Excel Basics for Data Analysis",
                "issuer": "Coursera IBM",
                "issued_at": "2025-04",
            }
        ],
    )

    assert [e.field_of_study for e in cv.educations] == [
        "Excel Basics for Data Analysis"
    ]
    # Queda la copia con más datos (la de los estudios) y se va el certificado.
    assert cv.educations[0].started_at == "2025-04"
    assert cv.certifications == []


def test_the_match_ignores_accents_case_and_punctuation() -> None:
    cv = _build(
        educations=[_education("Escuela Técnica N°5", "Programación Web")],
        certifications=[
            {"name": "programacion  web.", "issuer": "ESCUELA TECNICA N 5"}
        ],
    )

    assert cv.certifications == []


def test_a_title_written_as_degree_level_also_matches() -> None:
    cv = _build(
        educations=[
            {
                "institution": "Streambe",
                "field_of_study": "",
                "degree_level": "Full Stack",
            }
        ],
        certifications=[{"name": "Full Stack", "issuer": "Streambe"}],
    )

    assert cv.certifications == []


def test_a_certificate_without_issuer_still_matches_by_name() -> None:
    cv = _build(
        educations=[_education("Coursera Google", "CyberSecurity Training")],
        certifications=[{"name": "CyberSecurity Training", "issuer": ""}],
    )

    assert cv.certifications == []


def test_a_certificate_the_studies_do_not_list_stays() -> None:
    cv = _build(
        educations=[_education("Coursera IBM", "Excel Basics for Data Analysis")],
        certifications=[
            {"name": "Excel Basics for Data Analysis", "issuer": "Coursera IBM"},
            {"name": "AWS Cloud Practitioner", "issuer": "Amazon"},
        ],
    )

    assert [c.name for c in cv.certifications] == ["AWS Cloud Practitioner"]


def test_the_same_title_from_another_institution_is_another_course() -> None:
    cv = _build(
        educations=[_education("Coursera IBM", "Excel Basics")],
        certifications=[{"name": "Excel Basics", "issuer": "Udemy"}],
    )

    assert [c.issuer for c in cv.certifications] == ["Udemy"]


def test_without_studies_every_certificate_stays() -> None:
    cv = _build(certifications=[{"name": "Excel Basics", "issuer": "Coursera"}])

    assert [c.name for c in cv.certifications] == ["Excel Basics"]


def test_two_identical_courses_in_the_studies_are_both_kept() -> None:
    # No se deduplican los estudios entre sí: solo el certificado repetido.
    cv = _build(
        educations=[
            _education("Coursera IBM", "Excel Basics"),
            _education("Coursera IBM", "Excel Basics"),
        ]
    )

    assert len(cv.educations) == 2


# --- el contacto del CV ----------------------------------------------------------


def _world(document_type: str) -> FakeSupabase:
    supabase = FakeSupabase()
    supabase.storage.files["user-1/cv.pdf"] = b"%PDF-1.4 fake"
    supabase.tables["uploaded_documents"].append(
        {
            "id": "document-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": document_type,
            "storage_path": "user-1/cv.pdf",
            "status": "pending",
        }
    )
    return supabase


def _use_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_extract_pdf_content(_path: Any) -> PdfContent:
        return PdfContent("texto del CV", None)

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return CVStructuredData(
            contact=ParsedContact(
                full_name="Lucía Ferreyra",
                email="lucia.demo@example.com",
                phone="+54 11 5555-0000",
                location="Buenos Aires",
                linkedin_url="https://www.linkedin.com/in/lucia-demo",
            ),
            skills=[ParsedSkill(name="Python", category="other", level="advanced")],
        )

    monkeypatch.setattr(parsing, "extract_pdf_content", fake_extract_pdf_content)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)


class VectorGateway:
    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 4 for _text in texts]


@pytest.mark.asyncio
async def test_a_cv_saves_the_contact_the_reader_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world("cv")
    _use_parser(monkeypatch)

    result = await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=VectorGateway(),  # type: ignore[arg-type]
    )

    stored = supabase.tables["uploaded_documents"][0]["parsed_data"]
    assert stored["contact"] == {
        "full_name": "Lucía Ferreyra",
        "email": "lucia.demo@example.com",
        "phone": "+54 11 5555-0000",
        "location": "Buenos Aires",
        "linkedin_url": "https://www.linkedin.com/in/lucia-demo",
    }
    assert result["contact"] == stored["contact"]


@pytest.mark.asyncio
async def test_the_saved_contact_is_the_header_of_the_downloadable_cv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world("cv")
    _use_parser(monkeypatch)
    await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=VectorGateway(),  # type: ignore[arg-type]
    )

    cv = build_printable_cv(
        profile={},
        primary_cv=supabase.tables["uploaded_documents"][0],
        account_email="cuenta@example.com",
        skills=[],
        experiences=[],
        educations=[],
        languages=[],
        certifications=[],
    )

    assert cv.contact.full_name == "Lucía Ferreyra"
    assert cv.contact.phone == "+54 11 5555-0000"
    assert cv.contact.location == "Buenos Aires"


@pytest.mark.asyncio
async def test_a_linkedin_document_does_not_store_the_contact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world("linkedin")
    _use_parser(monkeypatch)

    await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=VectorGateway(),  # type: ignore[arg-type]
    )

    assert "contact" not in supabase.tables["uploaded_documents"][0]["parsed_data"]
