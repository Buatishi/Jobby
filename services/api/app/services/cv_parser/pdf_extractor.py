import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pdfplumber
from pdfplumber.page import Page

from app.services.cv_parser.errors import CVParsingError
from app.services.cv_parser.pdf_layout import FormatFlags, PdfContent, read_layout

logger = logging.getLogger(__name__)

MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024
# Un CV real no pasa de unas pocas hojas: más páginas es abuso o no es un CV.
MAX_PDF_PAGES = 20
PDF_SIGNATURE = b"%PDF-"
# Un CV de 20 páginas no llega a 100 000 caracteres: más es un PDF armado para pesar.
MAX_EXTRACTED_TEXT_CHARS = 200_000

# La lectura corre en un proceso hijo (`pdf_worker`) con topes de memoria y de CPU. Este
# plazo de reloj es la última red y es holgado a propósito: la instancia gratuita de
# Render tiene una fracción de CPU, y una lectura normal son unos segundos de CPU que
# ahí pueden verse como decenas de segundos de reloj.
PDF_WORKER_TIMEOUT_SECONDS = 120.0
# El texto ya viene acotado por `MAX_EXTRACTED_TEXT_CHARS`; esto cubre el JSON.
MAX_WORKER_OUTPUT_BYTES = 4 * 1024 * 1024
WORKER_MODULE = "app.services.cv_parser.pdf_worker"
# services/api: de ahí se importa `app`, sin importar desde dónde arrancó la API.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
# Lo único que el hijo necesita del entorno. El resto (llaves de Supabase, de los
# proveedores de IA, el secreto del webhook) no se le pasa: lee un archivo ajeno.
_WORKER_ENV_ALLOWLIST = frozenset(
    {"PATH", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL"}
)


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

    if len(content.text) > MAX_EXTRACTED_TEXT_CHARS:
        return PdfContent(
            text=content.text[:MAX_EXTRACTED_TEXT_CHARS],
            format_flags=content.format_flags,
        )
    return content


def _worker_command(file_path: Path) -> list[str]:
    # -P: no antepone la carpeta actual al path de importación (el PYTHONPATH sí rige).
    return [sys.executable, "-P", "-m", WORKER_MODULE, str(file_path)]


def _worker_environment() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in _WORKER_ENV_ALLOWLIST
    }
    env["PYTHONPATH"] = str(_PROJECT_ROOT)
    env["PYTHONUTF8"] = "1"
    return env


def _worker_working_directory() -> str:
    # Una carpeta sin `.env`: el hijo no carga la configuración con las llaves.
    return tempfile.gettempdir()


def _run_worker(command: list[str]) -> tuple[bytes, int | None, bool]:
    """Corre el hijo y devuelve (salida, código de salida, si venció el plazo)."""
    expired = threading.Event()
    with subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=_worker_environment(),
        cwd=_worker_working_directory(),
    ) as process:

        def expire() -> None:
            expired.set()
            process.kill()

        timer = threading.Timer(PDF_WORKER_TIMEOUT_SECONDS, expire)
        timer.start()
        try:
            assert process.stdout is not None
            output = process.stdout.read(MAX_WORKER_OUTPUT_BYTES + 1)
            if len(output) > MAX_WORKER_OUTPUT_BYTES:
                process.kill()
            process.wait()
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
        return output, process.returncode, expired.is_set()


def _decode_answer(output: bytes) -> PdfContent:
    """La línea de JSON del hijo, validada: no se confía en lo que haya impreso."""
    try:
        answer = json.loads(output)
        if not isinstance(answer, dict):
            raise ValueError("respuesta que no es un objeto")
        if answer.get("ok") is True:
            text = answer["text"]
            if not isinstance(text, str):
                raise ValueError("texto que no es texto")
            raw_flags = answer["format_flags"]
            flags = None if raw_flags is None else FormatFlags.from_dict(raw_flags)
            return PdfContent(text=text, format_flags=flags)
        code, message = answer["code"], answer["message"]
        if answer.get("ok") is not False or not isinstance(code, str):
            raise ValueError("respuesta sin resultado")
        if not isinstance(message, str):
            raise ValueError("mensaje que no es texto")
    except (ValueError, KeyError, TypeError) as exc:
        raise CVParsingError("No se pudo leer el PDF.", "PDF_READ_ERROR") from exc
    raise CVParsingError(message, code)


async def _read_in_worker(file_path: Path) -> PdfContent:
    output, returncode, expired = await asyncio.to_thread(
        _run_worker, _worker_command(file_path)
    )
    if expired:
        raise CVParsingError("El PDF tardó demasiado en leerse.", "PDF_TIMEOUT")
    if len(output) > MAX_WORKER_OUTPUT_BYTES:
        raise CVParsingError("No se pudo leer el PDF.", "PDF_READ_ERROR")
    if returncode != 0:
        # El sistema lo cortó (memoria o CPU) o se cayó: el PDF pesa demasiado.
        logger.warning("El proceso que lee el PDF terminó con código %s.", returncode)
        raise CVParsingError(
            "El PDF es demasiado pesado o complejo para leerlo.", "PDF_TOO_COMPLEX"
        )
    return _decode_answer(output)


async def extract_pdf_content(file_path: str | Path) -> PdfContent:
    path = Path(file_path)
    # Lo barato se comprueba acá: un archivo que no es PDF no arranca un proceso.
    await asyncio.to_thread(_validate_pdf_path, path)
    return await _read_in_worker(path)


async def extract_pdf_text(file_path: str | Path) -> str:
    return (await extract_pdf_content(file_path)).text
