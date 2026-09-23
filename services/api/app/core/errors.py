import logging
from typing import Any

import sentry_sdk
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def error_response(
    message: str,
    code: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": message, "code": code, "details": details or {}},
    )


async def http_error_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if isinstance(exc, StarletteHTTPException):
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)

        return error_response(
            message=str(exc.detail),
            code="HTTP_ERROR",
            status_code=exc.status_code,
        )

    return error_response(
        message="Error inesperado",
        code="INTERNAL_ERROR",
        status_code=500,
    )


async def supabase_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Último recurso para un error del cliente de Supabase que nadie manejó.

    Sin esto FastAPI responde 500 en texto plano y se rompe el formato único de error.
    El detalle interno queda en el registro, no en la respuesta.
    """
    logger.exception("Error de Supabase sin manejar en %s", request.url.path)
    sentry_sdk.capture_exception(exc)
    return error_response(
        message="Error inesperado",
        code="INTERNAL_ERROR",
        status_code=500,
    )


async def validation_error_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return error_response(
            message="Error inesperado",
            code="INTERNAL_ERROR",
            status_code=500,
        )

    return error_response(
        message="Datos de entrada inválidos",
        code="VALIDATION_ERROR",
        status_code=400,
        details={"errors": exc.errors()},
    )
