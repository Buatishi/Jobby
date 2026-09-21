"""Mensajes de error aptos para mostrar al usuario.

Las excepciones internas pueden contener nombres de variables de entorno, URLs o
detalles de proveedores. Nunca se devuelven tal cual: se traducen a un texto seguro y el
detalle queda solo en los logs del servidor.
"""

from app.services.ai_gateway.errors import (
    PremiumRequiredError,
    ProviderUnavailableError,
)
from app.services.cv_parser.errors import CVParsingError
from app.services.scraper.playwright_scraper import ScraperBlockedError
from app.services.scraper.url_guard import UnsafeUrlError

GENERIC_TASK_ERROR = "No pudimos completar la tarea. Probá de nuevo en unos minutos."


def public_error_message(exc: BaseException | None) -> str:
    if isinstance(exc, ProviderUnavailableError):
        return (
            "El servicio de IA no está disponible en este momento. "
            "Probá de nuevo más tarde."
        )
    if isinstance(exc, PremiumRequiredError):
        return "Esta función requiere el plan premium."
    if isinstance(exc, UnsafeUrlError):
        return "La URL indicada no es válida o no está permitida."
    if isinstance(exc, ScraperBlockedError):
        return (
            "No pudimos leer la página indicada. "
            "Pegá el texto del puesto para continuar."
        )
    if isinstance(exc, CVParsingError):
        return (
            "No pudimos leer tu CV. Verificá que sea un PDF con texto seleccionable."
        )
    return GENERIC_TASK_ERROR
