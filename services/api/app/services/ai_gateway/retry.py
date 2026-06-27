import asyncio
from collections.abc import Awaitable, Callable


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
            if attempt == len(delays):
                break
            await asyncio.sleep(delays[attempt])

    if last_error is None:
        raise RuntimeError("Retry failed without an exception.")

    raise last_error
