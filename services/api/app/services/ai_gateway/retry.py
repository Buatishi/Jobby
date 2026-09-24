import asyncio
from collections.abc import Awaitable, Callable

import httpx

# Un 408 (tiempo agotado) o un 429 (demasiados pedidos) pueden andar en otro intento;
# otro 4xx, como una clave rechazada, falla igual: reintentarlo solo demora el error.
RETRYABLE_CLIENT_ERRORS = frozenset({408, 429})


def worth_retrying(exc: BaseException) -> bool:
    error: BaseException | None = exc
    while error is not None:
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            return status_code >= 500 or status_code in RETRYABLE_CLIENT_ERRORS
        error = error.__cause__
    return True


async def retry_with_backoff[T](
    operation: Callable[[], Awaitable[T]],
    delays: tuple[float, ...],
) -> T:
    last_error: Exception | None = None

    for attempt in range(len(delays) + 1):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            if attempt == len(delays) or not worth_retrying(exc):
                break
            await asyncio.sleep(delays[attempt])

    if last_error is None:
        raise RuntimeError("Retry failed without an exception.")

    raise last_error
