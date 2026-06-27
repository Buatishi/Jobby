import asyncio
from collections.abc import AsyncIterator
from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.tasks import TaskResponse, TaskStatus
from app.tasks import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _normalize_task_status(state: str) -> TaskStatus:
    normalized = state.lower()
    if normalized in {"pending", "received", "retry", "started"}:
        return "processing" if normalized == "started" else "pending"
    if normalized == "success":
        return "done"
    if normalized in {"failure", "revoked"}:
        return "failed"
    return "pending"


def get_task_response(task_id: str) -> TaskResponse:
    result = AsyncResult(task_id, app=celery_app)
    status = _normalize_task_status(result.state)
    payload: Any | None = None
    error: str | None = None

    if result.ready():
        if result.successful():
            payload = result.result
        else:
            error = str(result.result)

    return TaskResponse(task_id=task_id, status=status, result=payload, error=error)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str) -> TaskResponse:
    return get_task_response(task_id)


async def _task_event_stream(task_id: str) -> AsyncIterator[str]:
    while True:
        response = get_task_response(task_id)
        event = "complete" if response.status in {"done", "failed"} else "status"
        yield f"event: {event}\ndata: {response.model_dump_json()}\n\n"

        if response.status in {"done", "failed"}:
            break

        await asyncio.sleep(1)


@router.get("/{task_id}/stream")
async def stream_task_status(task_id: str) -> StreamingResponse:
    return StreamingResponse(
        _task_event_stream(task_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
