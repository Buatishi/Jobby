from pathlib import Path

import httpx
import pytest

from app.services.cv_parser import (
    CVParsingError,
    CVStructuredData,
    ai_structurer,
    extract_pdf_text,
)
from app.services.cv_parser.ai_structurer import ParsedSkill
from app.services.cv_parser.merge_logic import merge_parsed_skills


def _write_minimal_pdf(path: Path, text: str) -> None:
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            f"<< /Length {len(f'BT /F1 24 Tf 72 720 Td ({escaped_text}) Tj ET')} >>\n"
            f"stream\nBT /F1 24 Tf 72 720 Td ({escaped_text}) Tj ET\nendstream"
        ).encode(),
    ]

    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode())
        content.extend(obj)
        content.extend(b"\nendobj\n")

    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode())
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )

    path.write_bytes(bytes(content))


@pytest.mark.asyncio
async def test_extract_pdf_text_reads_valid_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cv.pdf"
    _write_minimal_pdf(pdf_path, "Python FastAPI Supabase")

    text = await extract_pdf_text(pdf_path)

    assert "Python FastAPI Supabase" in text


@pytest.mark.asyncio
async def test_extract_pdf_text_rejects_invalid_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cv.pdf"
    pdf_path.write_text("not a real pdf", encoding="utf-8")

    with pytest.raises(CVParsingError) as exc_info:
        await extract_pdf_text(pdf_path)

    assert exc_info.value.code == "PDF_READ_ERROR"


def test_merge_parsed_skills_deduplicates_and_keeps_confirmed() -> None:
    parsed_data = CVStructuredData(
        skills=[
            ParsedSkill(name="Python", category="technical", level="expert"),
            ParsedSkill(name="FastAPI", category="technical", level="advanced"),
        ]
    )
    existing_skills = [
        {
            "name": "python",
            "category": "technical",
            "level": "intermediate",
            "confirmed": True,
            "in_cv": False,
        }
    ]

    merged = merge_parsed_skills(parsed_data, existing_skills)

    python_skill = next(skill for skill in merged if skill["name"] == "python")
    fastapi_skill = next(skill for skill in merged if skill["name"] == "FastAPI")
    assert python_skill["level"] == "intermediate"
    assert python_skill["confirmed"] is True
    assert fastapi_skill["in_cv"] is True
    assert len(merged) == 2


def test_deepseek_api_key_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai_structurer.settings, "deepseek_api_key", ' "sk-test" ')

    assert ai_structurer._deepseek_api_key() == "sk-test"


def test_structured_payload_normalization_accepts_ai_variants() -> None:
    normalized = ai_structurer._normalize_structured_payload(
        {
            "data": {
                "skills": [
                    {"skill_name": "Python", "type": None, "proficiency": "Senior"},
                    {"category": "technical"},
                ],
                "experiences": [
                    {
                        "employer": "Acme",
                        "role": "Backend Engineer",
                        "start_date": None,
                        "achievements": "Reduced latency",
                    }
                ],
                "educations": [{"school": "UBA", "degree": None}],
                "languages": [{"language": "English", "proficiency": None}],
                "certifications": [{"title": "AWS", "organization": "Amazon"}],
            }
        }
    )

    parsed = CVStructuredData.model_validate(normalized)

    assert parsed.skills[0].name == "Python"
    assert parsed.skills[0].category == "general"
    assert parsed.experiences[0].title == "Backend Engineer"
    assert parsed.experiences[0].achievements == ["Reduced latency"]
    assert parsed.languages[0].level == "unknown"
    assert len(parsed.skills) == 1


@pytest.mark.asyncio
async def test_deepseek_unauthorized_returns_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        status_code = 401

        def raise_for_status(self) -> None:
            request = httpx.Request("POST", ai_structurer.DEEPSEEK_CHAT_URL)
            response = httpx.Response(401, request=request)
            raise httpx.HTTPStatusError(
                "unauthorized",
                request=request,
                response=response,
            )

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(ai_structurer.settings, "deepseek_api_key", "bad-key")
    monkeypatch.setattr(ai_structurer.httpx, "AsyncClient", FakeClient)

    with pytest.raises(CVParsingError) as exc_info:
        await ai_structurer._call_deepseek("Python FastAPI")

    assert exc_info.value.code == "DEEPSEEK_UNAUTHORIZED"


@pytest.mark.asyncio
async def test_extract_pdf_text_rejects_files_over_ten_megabytes(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "cv.pdf"
    with pdf_path.open("wb") as pdf:
        pdf.truncate(10 * 1024 * 1024 + 1)

    with pytest.raises(CVParsingError) as error:
        await extract_pdf_text(pdf_path)

    assert error.value.code == "PDF_TOO_LARGE"
