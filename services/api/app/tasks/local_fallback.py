import asyncio
import threading
import time
from collections.abc import Callable, Coroutine
from typing import Any, Literal

from app.config import settings
from app.core.task_ids import new_task_id

TaskState = Literal["PENDING", "STARTED", "SUCCESS", "FAILURE"]

# Una tarea encadenada (por ejemplo el match que sigue a un analisis) espera su
# turno en lugar de fallar mientras la tarea que la encadena aun ocupa un cupo.
LOCAL_SLOT_WAIT_SECONDS = 300.0

# Una tarea terminada se guarda una hora para que el cliente lea el resultado y después
# se descarta. Sin este límite, cada tarea (con su resultado) quedaba en memoria para
# siempre.
FINISHED_TASK_RETENTION_SECONDS = 60 * 60

# Reloj inyectable: los tests lo reemplazan para simular el paso del tiempo.
_now = time.monotonic


class LocalTaskResult:
    def __init__(self, task_id: str, state: TaskState, result: Any = None) -> None:
        self.id = task_id
        self.state = state
        self.result = result
        self.finished_at = _now() if self.ready() else None

    def ready(self) -> bool:
        return self.state in {"SUCCESS", "FAILURE"}

    def successful(self) -> bool:
        return self.state == "SUCCESS"


_tasks: dict[str, LocalTaskResult] = {}
_lock = threading.Lock()
_semaphore = threading.BoundedSemaphore(settings.local_task_max_concurrency)


def is_local_mode() -> bool:
    return settings.task_execution_mode.lower() == "local"


def _forget_expired_tasks() -> None:
    """Descarta las tareas terminadas hace más de una hora. Requiere `_lock` tomado."""
    now = _now()
    expired = [
        task_id
        for task_id, task in _tasks.items()
        if task.finished_at is not None
        and now - task.finished_at > FINISHED_TASK_RETENTION_SECONDS
    ]
    for task_id in expired:
        del _tasks[task_id]


def get_local_task(task_id: str) -> LocalTaskResult | None:
    with _lock:
        _forget_expired_tasks()
        return _tasks.get(task_id)


def enqueue_local_task(
    task_factory: Callable[[], Coroutine[Any, Any, Any]],
    *,
    prefix: str,
    owner_id: str,
    wait_for_slot: bool = False,
) -> str:
    task_id = new_task_id(owner_id, prefix)
    with _lock:
        _forget_expired_tasks()
        _tasks[task_id] = LocalTaskResult(task_id, "PENDING")

    def runner() -> None:
        if wait_for_slot:
            acquired = _semaphore.acquire(timeout=LOCAL_SLOT_WAIT_SECONDS)
        else:
            acquired = _semaphore.acquire(blocking=False)
        if not acquired:
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
