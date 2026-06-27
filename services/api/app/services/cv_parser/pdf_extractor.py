import asyncio
from pathlib import Path

import pdfplumber

from app.services.cv_parser.errors import CVParsingError

MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024


def _validate_pdf_path(file_path: Path) -> None:
    if file_path.suffix.lower() != ".pdf":
        raise CVParsingError("El archivo debe ser PDF.", "INVALID_PDF_TYPE")

    if not file_path.exists() or not file_path.is_file():
        raise CVParsingError("El archivo PDF no existe.", "PDF_NOT_FOUND")

    if file_path.stat().st_size > MAX_PDF_SIZE_BYTES:
        raise CVParsingError("El PDF supera el límite de 10MB.", "PDF_TOO_LARGE")


def _extract_pdf_text_sync(file_path: Path) -> str:
    _validate_pdf_path(file_path)

    try:
        with pdfplumber.open(file_path) as pdf:
            page_text = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        raise CVParsingError("No se pudo leer el PDF.", "PDF_READ_ERROR") from exc

    text = "\n\n".join(part.strip() for part in page_text if part.strip()).strip()
    if not text:
        raise CVParsingError(
            "No se encontró texto extraíble en el PDF.",
            "PDF_EMPTY_TEXT",
        )

    return text


async def extract_pdf_text(file_path: str | Path) -> str:
    return await asyncio.to_thread(_extract_pdf_text_sync, Path(file_path))
