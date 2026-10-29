"""La lectura del PDF corre en un proceso aparte, con tope de memoria, CPU y tiempo.

Un PDF lo arma quien sube el archivo: un flujo comprimido que se expande a GB, miles de
objetos o un recorrido lento podían agotar los 512 MB de la API (que comparte con las
tareas locales) o dejar ocupado uno de sus dos cupos. Leerlo en un hilo no permitía
ponerle tope ni cancelarlo. En un proceso hijo el sistema puede cortarlo sin tocar a la
API, y la API solo recibe un resultado chico o un error.

Estas pruebas usan el proceso hijo de verdad; el resto de la suite lee en proceso (ver
el fixture `_read_pdfs_in_process` de `tests/conftest.py`).
"""

import os
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from app.services.cv_parser import CVParsingError, pdf_extractor, pdf_worker
from app.services.cv_parser.pdf_layout import FormatFlags
from tests.pdf_builder import Page, Text, build_pdf

_REAL_READ_IN_WORKER = pdf_extractor._read_in_worker
MIB = 1024 * 1024


@pytest.fixture(autouse=True)
def _real_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_extractor, "_read_in_worker", _REAL_READ_IN_WORKER)


def _page() -> Page:
    lines = [f"Linea {index} del documento" for index in range(16)]
    return Page(texts=[Text(60, 60 + 14 * i, line) for i, line in enumerate(lines)])


def _write(tmp_path: Path, *pages: Page) -> Path:
    path = tmp_path / "cv.pdf"
    path.write_bytes(build_pdf(list(pages)))
    return path


def _fake_worker(monkeypatch: pytest.MonkeyPatch, code: str) -> None:
    """Reemplaza el programa del hijo por un script que simula uno que se porta mal."""
    monkeypatch.setattr(
        pdf_extractor, "_worker_command", lambda _path: [sys.executable, "-c", code]
    )


# --- el hijo de verdad ----------------------------------------------------------------


async def test_the_worker_reads_the_same_content_as_the_process_itself(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path, _page())

    content = await pdf_extractor.extract_pdf_content(path)

    assert content == pdf_extractor._extract_pdf_content_sync(path)
    assert "Linea 0 del documento" in content.text
    assert content.format_flags is not None


async def test_an_error_raised_inside_the_worker_keeps_its_code(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path, *[_page()] * (pdf_extractor.MAX_PDF_PAGES + 1))

    with pytest.raises(CVParsingError) as error:
        await pdf_extractor.extract_pdf_content(path)

    assert error.value.code == "PDF_TOO_MANY_PAGES"


async def test_a_file_that_is_not_a_pdf_never_starts_a_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_worker(_path: Path) -> list[str]:
        raise AssertionError("no hay nada que leer")

    monkeypatch.setattr(pdf_extractor, "_worker_command", no_worker)
    path = tmp_path / "cv.pdf"
    path.write_bytes(b"PK\x03\x04" + b"0" * 2048)

    with pytest.raises(CVParsingError) as error:
        await pdf_extractor.extract_pdf_content(path)

    assert error.value.code == "PDF_READ_ERROR"


# --- un hijo que se porta mal no afecta a la API --------------------------------------


async def test_a_worker_that_never_answers_is_killed_at_the_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_worker(monkeypatch, "import time; time.sleep(60)")
    monkeypatch.setattr(pdf_extractor, "PDF_WORKER_TIMEOUT_SECONDS", 0.5)

    started = time.monotonic()
    with pytest.raises(CVParsingError) as error:
        await pdf_extractor.extract_pdf_content(_write(tmp_path, _page()))

    assert error.value.code == "PDF_TIMEOUT"
    # Sin matar al hijo, esperar su salida llevaba los 60 s.
    assert time.monotonic() - started < 10


async def test_a_worker_that_dies_is_reported_and_the_caller_keeps_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Lo que ve la API cuando el sistema mata al hijo por memoria o por CPU.
    _fake_worker(monkeypatch, "import os; os._exit(137)")

    with pytest.raises(CVParsingError) as error:
        await pdf_extractor.extract_pdf_content(_write(tmp_path, _page()))

    assert error.value.code == "PDF_TOO_COMPLEX"


async def test_an_oversized_answer_is_refused_without_reading_it_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_worker(monkeypatch, "import sys; sys.stdout.write('x' * 6_000_000)")

    with pytest.raises(CVParsingError) as error:
        await pdf_extractor.extract_pdf_content(_write(tmp_path, _page()))

    assert error.value.code == "PDF_READ_ERROR"


@pytest.mark.parametrize(
    "answer",
    [
        "no soy json",
        "[]",
        '{"ok": true}',
        '{"ok": true, "text": 5, "format_flags": null}',
        '{"ok": true, "text": "x", "format_flags": {"has_tables": true}}',
        '{"ok": false}',
    ],
)
async def test_an_answer_with_the_wrong_shape_is_a_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: str
) -> None:
    _fake_worker(monkeypatch, f"print({answer!r})")

    with pytest.raises(CVParsingError) as error:
        await pdf_extractor.extract_pdf_content(_write(tmp_path, _page()))

    assert error.value.code == "PDF_READ_ERROR"


def test_the_worker_does_not_inherit_secrets_from_the_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El hijo lee un archivo que no es de confianza: no hereda llaves ni `.env`."""
    for name in (
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_JWT_SECRET",
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "LEMONSQUEEZY_WEBHOOK_SECRET",
    ):
        monkeypatch.setenv(name, "valor-secreto")

    env = pdf_extractor._worker_environment()

    assert not any("valor-secreto" in value for value in env.values())
    assert "PATH" in {key.upper() for key in env}
    # Encuentra el paquete `app` sin depender de la carpeta desde donde arrancó la API.
    assert (Path(env["PYTHONPATH"]) / "app" / "main.py").is_file()
    assert Path(pdf_extractor._worker_working_directory()) != Path(env["PYTHONPATH"])


# --- los topes que aplica el hijo -----------------------------------------------------


class _FakeResource:
    RLIMIT_AS = 9
    RLIMIT_CPU = 0

    def __init__(self) -> None:
        self.calls: list[tuple[int, tuple[int, int]]] = []

    def setrlimit(self, which: int, limits: tuple[int, int]) -> None:
        self.calls.append((which, limits))


def test_the_worker_may_only_grow_by_its_budget_beyond_what_it_already_uses(
    tmp_path: Path,
) -> None:
    fake = _FakeResource()
    oom_file = tmp_path / "oom_score_adj"
    oom_file.write_text("0")

    applied = pdf_worker.apply_resource_limits(
        memory_budget_bytes=200 * MIB,
        cpu_seconds=20,
        resource_module=fake,
        address_space_bytes=lambda: 700 * MIB,
        oom_score_path=oom_file,
    )

    assert applied is True
    # El tope es sobre lo que ya ocupa (intérprete y librerías ya cargados): lo que se
    # limita es cuánto puede crecer al leer el PDF.
    assert (fake.RLIMIT_AS, (900 * MIB, 900 * MIB)) in fake.calls
    assert (fake.RLIMIT_CPU, (20, 20)) in fake.calls
    # Si el contenedor se queda sin memoria, que el sistema mate a este proceso y no a
    # la API.
    assert oom_file.read_text() == "1000"


def test_without_resource_limits_the_worker_still_runs(tmp_path: Path) -> None:
    """En Windows (desarrollo) no existen los límites del sistema: queda el plazo."""
    applied = pdf_worker.apply_resource_limits(
        memory_budget_bytes=200 * MIB,
        cpu_seconds=20,
        resource_module=None,
        address_space_bytes=lambda: None,
        oom_score_path=tmp_path / "no-existe" / "oom_score_adj",
    )

    assert applied is False


def test_the_worker_prints_one_json_line_with_the_content(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(tmp_path, _page())

    exit_code = pdf_worker.main([str(path)], limits=lambda: True)

    assert exit_code == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    assert '"ok": true' in lines[0]
    assert "Linea 0 del documento" in lines[0]


def test_the_worker_reports_a_cv_error_as_data(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "vacio.pdf"
    path.write_bytes(b"%PDF-1.4\n")

    exit_code = pdf_worker.main([str(path)], limits=lambda: True)

    assert exit_code == 0
    assert '"ok": false' in capsys.readouterr().out


def test_the_text_that_comes_back_is_capped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pdf_extractor, "MAX_EXTRACTED_TEXT_CHARS", 30)

    content = pdf_extractor._extract_pdf_content_sync(_write(tmp_path, _page()))

    assert len(content.text) == 30


# --- la forma de las banderas que viaja entre procesos --------------------------------


def test_format_flags_survive_the_trip_between_processes() -> None:
    flags = FormatFlags(
        has_tables=True, multi_column=False, has_images=True, headers=["EXPERIENCIA"]
    )

    assert FormatFlags.from_dict(flags.to_dict()) == flags


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"has_tables": True, "multi_column": False, "has_images": True},
        {"has_tables": "si", "multi_column": False, "has_images": True, "headers": []},
        {"has_tables": True, "multi_column": False, "has_images": True, "headers": "x"},
        {"has_tables": True, "multi_column": False, "has_images": True, "headers": [1]},
    ],
)
def test_format_flags_from_a_wrong_shape_are_rejected(data: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        FormatFlags.from_dict(data)


def test_the_process_can_start_a_python_worker_from_any_directory() -> None:
    """El hijo no depende de la carpeta actual de la API: ni de su `.env`."""
    assert os.path.isabs(pdf_extractor._worker_working_directory())
