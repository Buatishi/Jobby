import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Annotated, Any

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.public_errors import public_error_message
from app.core.task_ids import task_belongs_to
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.models.tasks import TaskResponse, TaskStatus
from app.tasks import celery_app
from app.tasks.local_fallback import get_local_task, is_local_mode

logger = logging.getLogger("jobmatch.tasks")

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Una tarea que nunca termina (por ejemplo sin worker) no debe dejar el stream abierto.
STREAM_MAX_SECONDS = 15 * 60

TASK_UNAVAILABLE_MESSAGE = (
    "La tarea ya no está disponible: el servidor se reinició o pasó demasiado tiempo. "
    "Probá de nuevo."
)


def _normalize_task_status(state: str) -> TaskStatus:
    normalized = state.lower()
    if normalized in {"pending", "received", "retry", "started"}:
        return "processing" if normalized == "started" else "pending"
    if normalized == "success":
        return "done"
    if normalized in {"failure", "revoked"}:
        return "failed"
    return "pending"


def _failure_message(task_id: str, error: Any) -> str:
    logger.warning("Task %s failed: %r", task_id, error)
    return public_error_message(error if isinstance(error, BaseException) else None)


def get_task_response(task_id: str) -> TaskResponse:
    local_result = get_local_task(task_id)
    if local_result is not None:
        status_value = _normalize_task_status(local_result.state)
        local_payload: Any | None = None
        local_error: str | None = None
        if local_result.ready():
            if local_result.successful():
                local_payload = local_result.result
            else:
                local_error = _failure_message(task_id, local_result.result)
        return TaskResponse(
            task_id=task_id,
            status=status_value,
            result=local_payload,
            error=local_error,
        )

    if is_local_mode():
        # Sin worker, una tarea que no está en memoria se perdió con un reinicio o
        # ya venció. Celery devolvería "pending" y el cliente esperaría hasta el
        # tiempo límite del stream.
        return TaskResponse(
            task_id=task_id,
            status="failed",
            error=TASK_UNAVAILABLE_MESSAGE,
        )

    result = AsyncResult(task_id, app=celery_app)
    status_value = _normalize_task_status(result.state)
    payload: Any | None = None
    error: str | None = None

    if result.ready():
        if result.successful():
            payload = result.result
        else:
            error = _failure_message(task_id, result.result)

    return TaskResponse(
        task_id=task_id,
        status=status_value,
        result=payload,
        error=error,
    )


def _ensure_owner(task_id: str, current_user: CurrentUser) -> None:
    # Misma respuesta para "no existe" y "no es tuya": no revela ids ajenos.
    if not task_belongs_to(task_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Tarea no encontrada",
                "code": "TASK_NOT_FOUND",
                "details": {},
            },
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> TaskResponse:
    _ensure_owner(task_id, current_user)
    return await asyncio.to_thread(get_task_response, task_id)


async def _task_event_stream(task_id: str) -> AsyncIterator[str]:
    deadline = time.monotonic() + STREAM_MAX_SECONDS
    while True:
        response = await asyncio.to_thread(get_task_response, task_id)
        finished = response.status in {"done", "failed"}
        event = "complete" if finished else "status"
        yield f"event: {event}\ndata: {response.model_dump_json()}\n\n"

        if finished:
            return
        if time.monotonic() >= deadline:
            timeout = TaskResponse(
                task_id=task_id,
                status="failed",
                error="La tarea tardó demasiado en completarse. Probá de nuevo.",
            )
            yield f"event: complete\ndata: {timeout.model_dump_json()}\n\n"
            return

        await asyncio.sleep(1)


@router.get("/{task_id}/stream")
async def stream_task_status(
    task_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> StreamingResponse:
    _ensure_owner(task_id, current_user)
    return StreamingResponse(
        _task_event_stream(task_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
