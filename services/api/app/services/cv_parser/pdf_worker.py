"""Proceso hijo que lee un PDF con topes de memoria y de CPU.

Lo lanza ``pdf_extractor.extract_pdf_content``. El PDF lo arma quien sube el archivo:
un flujo comprimido que se expande a GB, miles de objetos o un recorrido lento podían
agotar los 512 MB de la API (que comparte con las tareas locales) o dejar ocupado uno de
sus dos cupos. En un proceso aparte el sistema operativo corta el exceso sin tocar a la
API, que solo recibe una línea de JSON con el texto o con el error.

Los topes se aplican con ``resource`` (Linux, que es donde corre la API). En Windows no
existen: ahí, en desarrollo, queda solo el plazo que le pone quien lo lanza.
"""

import json
import mmap
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from app.services.cv_parser.errors import CVParsingError
from app.services.cv_parser.pdf_extractor import _extract_pdf_content_sync

# Cuánto puede crecer el proceso al leer el PDF, además de lo que ya ocupa con el
# intérprete y las librerías cargadas. Un CV de 20 páginas necesita decenas de MB; la
# API comparte 512 MB con las tareas locales.
MEMORY_BUDGET_BYTES = 200 * 1024 * 1024
# Segundos de CPU, no de reloj: en la instancia gratuita de Render una lectura normal
# tarda unos segundos de CPU aunque el reloj marque bastante más.
CPU_SECONDS = 20
# Valor máximo: si el contenedor se queda sin memoria, el sistema elige a este proceso
# antes que a la API.
_OOM_SCORE_ADJ = "1000"
_OOM_SCORE_PATH = Path("/proc/self/oom_score_adj")


def _load_resource() -> Any:
    try:
        import resource
    except ImportError:  # Windows
        return None
    return resource


_RESOURCE = _load_resource()


def _current_address_space_bytes() -> int | None:
    """Tamaño actual del espacio de direcciones (Linux); `None` si no se puede leer."""
    try:
        with open("/proc/self/statm", encoding="ascii") as statm:
            pages = int(statm.read().split()[0])
        return pages * mmap.PAGESIZE
    except (OSError, ValueError, IndexError):
        return None


def apply_resource_limits(
    *,
    memory_budget_bytes: int = MEMORY_BUDGET_BYTES,
    cpu_seconds: int = CPU_SECONDS,
    resource_module: Any = _RESOURCE,
    address_space_bytes: Callable[[], int | None] = _current_address_space_bytes,
    oom_score_path: Path = _OOM_SCORE_PATH,
) -> bool:
    """Pone los topes del proceso. Devuelve si pudo aplicar los del sistema.

    El tope de memoria se mide sobre lo que el proceso ya ocupa: lo que se limita es
    cuánto puede crecer al leer el PDF, sin adivinar lo que pesan las librerías.
    """
    try:
        oom_score_path.write_text(_OOM_SCORE_ADJ, encoding="ascii")
    except OSError:
        pass  # Sin /proc (Windows, macOS) no hay a quién avisar.

    if resource_module is None:
        return False
    address_space = address_space_bytes()
    if address_space is not None:
        limit = address_space + memory_budget_bytes
        resource_module.setrlimit(resource_module.RLIMIT_AS, (limit, limit))
    resource_module.setrlimit(resource_module.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    return True


def main(
    argv: Sequence[str] | None = None,
    *,
    limits: Callable[[], object] = apply_resource_limits,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        sys.stderr.write("uso: pdf_worker <archivo.pdf>\n")
        return 2

    limits()
    answer: dict[str, Any]
    try:
        content = _extract_pdf_content_sync(Path(args[0]))
    except CVParsingError as exc:
        answer = {"ok": False, "code": exc.code, "message": exc.message}
    except Exception:
        # Incluye el MemoryError de haber llegado al tope: un PDF que no se puede leer.
        answer = {
            "ok": False,
            "code": "PDF_READ_ERROR",
            "message": "No se pudo leer el PDF.",
        }
    else:
        flags = content.format_flags
        answer = {
            "ok": True,
            "text": content.text,
            "format_flags": flags.to_dict() if flags is not None else None,
        }
    sys.stdout.write(json.dumps(answer) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
