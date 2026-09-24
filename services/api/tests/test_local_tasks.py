"""Modo local de tareas (TASK_EXECUTION_MODE=local) para analisis, match y kits."""

import asyncio
import threading
import time
from types import SimpleNamespace
from typing import Any

import pytest

from app.tasks import analysis, local_fallback


def _wait_for(task_id: str, states: set[str], timeout: float = 5.0) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = local_fallback.get_local_task(task_id)
        if result is not None and result.state in states:
            return result
        time.sleep(0.01)
    raise AssertionError(f"la tarea {task_id} no llego a {states}")


def _forbidden(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("en modo local no se debe publicar en Celery")


@pytest.fixture
def local_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(local_fallback.settings, "task_execution_mode", "local")
    monkeypatch.setattr(local_fallback, "_semaphore", threading.BoundedSemaphore(2))
    monkeypatch.setattr(analysis.job_analysis_task, "apply_async", _forbidden)
    monkeypatch.setattr(analysis.match_task, "apply_async", _forbidden)
    monkeypatch.setattr(analysis.interview_kit_task, "apply_async", _forbidden)


def test_job_analysis_runs_in_process(
    local_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[Any, ...]] = []

    async def fake_run(*args: Any) -> dict[str, Any]:
        calls.append(args)
        return {"id": args[0]}

    monkeypatch.setattr(analysis, "run_job_analysis", fake_run)

    task_id = analysis.enqueue_job_analysis("job-1", "user-1", "text", None, "oferta")
    result = _wait_for(task_id, {"SUCCESS", "FAILURE"})

    assert result.state == "SUCCESS"
    assert result.result == {"id": "job-1"}
    assert calls == [("job-1", "user-1", "text", None, "oferta")]
    assert task_id.startswith("user-1.local-job-")


def test_match_runs_in_process(
    local_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_run(job_id: str, profile_id: str, user_id: str) -> dict[str, Any]:
        return {"job": job_id, "profile": profile_id, "user": user_id}

    monkeypatch.setattr(analysis, "run_match", fake_run)

    task_id = analysis.enqueue_match("job-1", "profile-1", "user-1")
    result = _wait_for(task_id, {"SUCCESS", "FAILURE"})

    assert result.state == "SUCCESS"
    assert result.result == {"job": "job-1", "profile": "profile-1", "user": "user-1"}
    assert task_id.startswith("user-1.local-match-")


def test_interview_kit_runs_in_process_and_mode_is_case_insensitive(
    local_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(local_fallback.settings, "task_execution_mode", "LOCAL")

    async def fake_run(kit_id: str, user_id: str) -> dict[str, Any]:
        return {"kit": kit_id, "user": user_id}

    monkeypatch.setattr(analysis, "run_interview_kit", fake_run)

    task_id = analysis.enqueue_interview_kit("kit-1", "user-1")
    result = _wait_for(task_id, {"SUCCESS", "FAILURE"})

    assert result.state == "SUCCESS"
    assert result.result == {"kit": "kit-1", "user": "user-1"}
    assert task_id.startswith("user-1.local-kit-")


def test_local_failure_is_captured_and_reported(
    local_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[Exception] = []

    async def failing_run(*_args: Any) -> dict[str, Any]:
        raise ValueError("boom")

    monkeypatch.setattr(analysis, "run_job_analysis", failing_run)
    monkeypatch.setattr(analysis, "capture_exception", captured.append)

    task_id = analysis.enqueue_job_analysis("job-1", "user-1", "text", None, "oferta")
    result = _wait_for(task_id, {"SUCCESS", "FAILURE"})

    assert result.state == "FAILURE"
    assert [str(error) for error in captured] == ["boom"]


def test_celery_mode_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    published: list[dict[str, Any]] = []

    def fake_apply_async(args: tuple[Any, ...], **kwargs: Any) -> Any:
        published.append({"args": args, **kwargs})
        return SimpleNamespace(id=kwargs["task_id"])

    monkeypatch.setattr(local_fallback.settings, "task_execution_mode", "celery")
    monkeypatch.setattr(analysis.job_analysis_task, "apply_async", fake_apply_async)
    monkeypatch.setattr(analysis.match_task, "apply_async", fake_apply_async)
    monkeypatch.setattr(analysis.interview_kit_task, "apply_async", fake_apply_async)
    monkeypatch.setattr(analysis, "enqueue_local_task", _forbidden)

    job_id = analysis.enqueue_job_analysis("job-1", "user-1", "text", None, "oferta")
    match_id = analysis.enqueue_match("job-1", "profile-1", "user-1")
    kit_id = analysis.enqueue_interview_kit("kit-1", "user-1")

    assert job_id.startswith("user-1.job-")
    assert match_id.startswith("user-1.match-")
    assert kit_id.startswith("user-1.kit-")
    assert [item["args"] for item in published] == [
        ("job-1", "user-1", "text", None, "oferta"),
        ("job-1", "profile-1", "user-1"),
        ("kit-1", "user-1"),
    ]


def test_only_the_chained_match_waits_for_a_slot(
    local_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: dict[str, dict[str, Any]] = {}

    def fake_enqueue(factory: Any, **kwargs: Any) -> str:
        calls[kwargs["prefix"]] = kwargs
        return "task-x"

    monkeypatch.setattr(analysis, "enqueue_local_task", fake_enqueue)

    analysis.enqueue_job_analysis("job-1", "user-1", "text", None, "oferta")
    analysis.enqueue_match("job-1", "profile-1", "user-1")
    analysis.enqueue_interview_kit("kit-1", "user-1")

    assert calls["local-match"]["wait_for_slot"] is True
    assert calls["local-job"].get("wait_for_slot", False) is False
    assert calls["local-kit"].get("wait_for_slot", False) is False


def test_chained_task_waits_but_direct_task_fails_when_capacity_is_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(local_fallback, "_semaphore", threading.BoundedSemaphore(1))
    release = threading.Event()

    async def holder() -> dict[str, Any]:
        await asyncio.to_thread(release.wait, 5)
        return {"held": True}

    async def quick() -> dict[str, Any]:
        return {"done": True}

    first = local_fallback.enqueue_local_task(holder, prefix="hold", owner_id="u")
    _wait_for(first, {"STARTED"})

    chained = local_fallback.enqueue_local_task(
        quick, prefix="chain", owner_id="u", wait_for_slot=True
    )
    direct = local_fallback.enqueue_local_task(quick, prefix="direct", owner_id="u")

    assert _wait_for(direct, {"FAILURE"}).state == "FAILURE"
    time.sleep(0.2)
    waiting = local_fallback.get_local_task(chained)
    assert waiting is not None and waiting.state == "PENDING"

    release.set()
    assert _wait_for(first, {"SUCCESS"}).state == "SUCCESS"
    assert _wait_for(chained, {"SUCCESS"}).result == {"done": True}


def test_finished_tasks_are_forgotten_after_the_retention_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [1000.0]
    monkeypatch.setattr(local_fallback, "_now", lambda: clock[0])
    monkeypatch.setattr(local_fallback, "_semaphore", threading.BoundedSemaphore(2))

    async def done() -> dict[str, Any]:
        return {"ok": True}

    task_id = local_fallback.enqueue_local_task(
        done, prefix="local-test", owner_id="user-1"
    )
    _wait_for(task_id, {"SUCCESS"})

    clock[0] += local_fallback.FINISHED_TASK_RETENTION_SECONDS - 1
    assert local_fallback.get_local_task(task_id) is not None

    clock[0] += 2
    assert local_fallback.get_local_task(task_id) is None


def test_running_tasks_are_kept_however_long_they_take(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [1000.0]
    monkeypatch.setattr(local_fallback, "_now", lambda: clock[0])
    monkeypatch.setattr(local_fallback, "_semaphore", threading.BoundedSemaphore(2))
    release = threading.Event()

    async def slow() -> dict[str, Any]:
        await asyncio.to_thread(release.wait, 5)
        return {"ok": True}

    task_id = local_fallback.enqueue_local_task(
        slow, prefix="local-test", owner_id="user-1"
    )
    _wait_for(task_id, {"STARTED"})
    clock[0] += local_fallback.FINISHED_TASK_RETENTION_SECONDS * 10

    try:
        assert local_fallback.get_local_task(task_id) is not None
    finally:
        release.set()
    assert _wait_for(task_id, {"SUCCESS"}).result == {"ok": True}
