import asyncio
import logging
from pathlib import Path

import pdfplumber
from pdfplumber.page import Page

from app.services.cv_parser.errors import CVParsingError
from app.services.cv_parser.pdf_layout import PdfContent, read_layout

logger = logging.getLogger(__name__)

MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024
# Un CV real no pasa de unas pocas hojas: más páginas es abuso o no es un CV.
MAX_PDF_PAGES = 20
PDF_SIGNATURE = b"%PDF-"


def _validate_pdf_path(file_path: Path) -> None:
    if file_path.suffix.lower() != ".pdf":
        raise CVParsingError("El archivo debe ser PDF.", "INVALID_PDF_TYPE")

    if not file_path.exists() or not file_path.is_file():
        raise CVParsingError("El archivo PDF no existe.", "PDF_NOT_FOUND")

    if file_path.stat().st_size > MAX_PDF_SIZE_BYTES:
        raise CVParsingError("El PDF supera el límite de 10MB.", "PDF_TOO_LARGE")

    # La extensión la elige quien sube el archivo: se comprueba también el contenido.
    with file_path.open("rb") as handle:
        if handle.read(len(PDF_SIGNATURE)) != PDF_SIGNATURE:
            raise CVParsingError("No se pudo leer el PDF.", "PDF_READ_ERROR")


def _join_pages(page_texts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in page_texts if part.strip()).strip()


def _read_pages(pages: list[Page]) -> PdfContent:
    """Texto en orden de lectura y banderas de formato (`None` si el análisis falla).

    El análisis de diseño es nuevo y corre sobre PDFs que la persona elige: un fallo
    suyo no puede dejar sin leer un CV que antes se leía. Se cae a la lectura plana y se
    omiten las banderas, así el ATS dirá «no se pudo evaluar» en vez de «sin problemas».
    """
    try:
        layout = read_layout(pages)
    except Exception as exc:
        # Solo la clase del error: el mensaje podría traer fragmentos del documento.
        logger.warning("No se pudo analizar el diseño del PDF: %s", type(exc).__name__)
        return PdfContent(
            text=_join_pages([page.extract_text() or "" for page in pages]),
            format_flags=None,
        )
    return PdfContent(
        text=_join_pages(layout.page_texts), format_flags=layout.format_flags
    )


def _extract_pdf_content_sync(file_path: Path) -> PdfContent:
    _validate_pdf_path(file_path)

    try:
        with pdfplumber.open(file_path) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                raise CVParsingError(
                    f"El PDF supera el límite de {MAX_PDF_PAGES} páginas.",
                    "PDF_TOO_MANY_PAGES",
                )
            content = _read_pages(list(pdf.pages))
    except CVParsingError:
        raise
    except Exception as exc:
        raise CVParsingError("No se pudo leer el PDF.", "PDF_READ_ERROR") from exc

    if not content.text:
        raise CVParsingError(
            "No se encontró texto extraíble en el PDF.",
            "PDF_EMPTY_TEXT",
        )

    return content


async def extract_pdf_content(file_path: str | Path) -> PdfContent:
    return await asyncio.to_thread(_extract_pdf_content_sync, Path(file_path))


async def extract_pdf_text(file_path: str | Path) -> str:
    return (await extract_pdf_content(file_path)).text
