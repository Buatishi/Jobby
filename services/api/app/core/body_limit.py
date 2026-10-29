"""Tope de tamaño del cuerpo de las peticiones.

Sin tope, una petición sin sesión podía hacer que el proceso cargara en memoria un
cuerpo de cientos de MB: el webhook de LemonSqueezy llama a ``request.body()`` antes de
mirar la firma, y FastAPI lee el cuerpo de una ruta con modelo antes de resolver la
autenticación. Los cuerpos reales son chicos (el más grande es el texto de un puesto,
de unos cientos de KB), así que 2 MiB sobra.

Es un middleware ASGI propio (no ``BaseHTTPMiddleware``) para cortar antes de leer: si
el pedido declara ``Content-Length`` por encima del tope se rechaza sin leerlo, y si
llega por partes se corta en cuanto lo recibido lo pasa.
"""

import json
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_REQUEST_BODY_BYTES = 2 * 1024 * 1024

_REFUSAL = json.dumps(
    {
        "error": "El cuerpo de la petición supera el tamaño permitido.",
        "code": "REQUEST_TOO_LARGE",
        "details": {},
    }
).encode()


class BodyTooLargeError(Exception):
    """Se recibió más cuerpo del permitido."""


def _contains_body_too_large(exc: BaseException) -> bool:
    if isinstance(exc, BodyTooLargeError):
        return True
    nested: Any = getattr(exc, "exceptions", ())
    return any(_contains_body_too_large(inner) for inner in nested)


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_REQUEST_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length")
        if declared and declared.isdigit() and int(declared) > self.max_bytes:
            await self._refuse(send)
            return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise BodyTooLargeError
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except BaseException as exc:
            if response_started or not _contains_body_too_large(exc):
                raise
            await self._refuse(send)

    async def _refuse(self, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(_REFUSAL)).encode()),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": _REFUSAL})
