import asyncio
import threading
import uuid
from collections.abc import Callable, Coroutine
from typing import Any, Literal

from app.config import settings

TaskState = Literal["PENDING", "STARTED", "SUCCESS", "FAILURE"]


class LocalTaskResult:
    def __init__(self, task_id: str, state: TaskState, result: Any = None) -> None:
        self.id = task_id
        self.state = state
        self.result = result

    def ready(self) -> bool:
        return self.state in {"SUCCESS", "FAILURE"}

    def successful(self) -> bool:
        return self.state == "SUCCESS"


_tasks: dict[str, LocalTaskResult] = {}
_lock = threading.Lock()
_semaphore = threading.BoundedSemaphore(settings.local_task_max_concurrency)


def get_local_task(task_id: str) -> LocalTaskResult | None:
    with _lock:
        return _tasks.get(task_id)


def enqueue_local_task(
    task_factory: Callable[[], Coroutine[Any, Any, Any]],
    *,
    prefix: str,
) -> str:
    task_id = f"{prefix}-{uuid.uuid4()}"
    with _lock:
        _tasks[task_id] = LocalTaskResult(task_id, "PENDING")

    def runner() -> None:
        if not _semaphore.acquire(blocking=False):
            error = RuntimeError(
                "Local task capacity exceeded. Configure Celery workers "
                "or retry when the current background task finishes."
            )
            with _lock:
                _tasks[task_id] = LocalTaskResult(task_id, "FAILURE", error)
            return

        with _lock:
            _tasks[task_id] = LocalTaskResult(task_id, "STARTED")
        try:
            result: Any = asyncio.run(task_factory())
        except Exception as exc:  # pragma: no cover - exercised through API flows
            with _lock:
                _tasks[task_id] = LocalTaskResult(task_id, "FAILURE", exc)
            return
        finally:
            _semaphore.release()

        with _lock:
            _tasks[task_id] = LocalTaskResult(task_id, "SUCCESS", result)

    thread = threading.Thread(target=runner, name=task_id, daemon=True)
    thread.start()
    return task_id
