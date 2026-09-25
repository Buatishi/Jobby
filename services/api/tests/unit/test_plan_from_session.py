"""El plan llega con la sesión: get_current_user lo lee junto con el rol.

Los endpoints no vuelven a pedirlo a la tabla users (era una consulta más por pedido).
En estas pruebas la tabla dice lo contrario que la sesión, y manda la sesión.
"""

from collections.abc import Awaitable, Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from tests.fakes import FakeSupabase, FakeTableQuery

JOBS_IN_HISTORY = 12


class RecordingSupabase(FakeSupabase):
    """Anota las tablas que consulta cada pedido."""

    def __init__(self) -> None:
        super().__init__()
        self.tables_read: list[str] = []

    def table(self, table_name: str) -> FakeTableQuery:
        self.tables_read.append(table_name)
        return super().table(table_name)


def _session(tier: str) -> Callable[[], Awaitable[CurrentUser]]:
    async def current_user() -> CurrentUser:
        return CurrentUser(
            id="user-1",
            supabase_uid="auth-user-1",
            email="person@example.com",
            tier=tier,
        )

    return current_user


@pytest.fixture()
def supabase() -> Iterator[RecordingSupabase]:
    fake = RecordingSupabase()
    fake.tables["job_descriptions"].extend(
        {
            "id": f"job-{index:02d}",
            "user_id": "user-1",
            "raw_text": "Puesto de prueba",
            "created_at": f"2026-09-{index + 1:02d}T12:00:00Z",
        }
        for index in range(JOBS_IN_HISTORY)
    )

    async def fake_client() -> RecordingSupabase:
        return fake

    app.dependency_overrides[get_supabase_client] = fake_client
    yield fake
    app.dependency_overrides.clear()


def _log_in(supabase: RecordingSupabase, *, session_tier: str, table_tier: str) -> None:
    supabase.tables["users"][0]["tier"] = table_tier
    app.dependency_overrides[get_current_user] = _session(session_tier)


@pytest.mark.parametrize(
    ("session_tier", "table_tier", "expected_jobs"),
    [("free", "premium", 10), ("premium", "free", JOBS_IN_HISTORY)],
)
def test_job_list_follows_the_session_plan(
    client: TestClient,
    supabase: RecordingSupabase,
    session_tier: str,
    table_tier: str,
    expected_jobs: int,
) -> None:
    _log_in(supabase, session_tier=session_tier, table_tier=table_tier)

    response = client.get("/api/v1/jobs")

    assert response.status_code == 200
    assert len(response.json()) == expected_jobs
    assert "users" not in supabase.tables_read


def test_job_analysis_counts_against_the_session_plan(
    client: TestClient,
    supabase: RecordingSupabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _log_in(supabase, session_tier="premium", table_tier="free")
    supabase.tables["master_profiles"][0]["completeness_pct"] = 100
    charged_tiers: list[str] = []

    async def fake_increment_rate_limit(_user_id: str, tier: str, _kind: Any) -> int:
        charged_tiers.append(tier)
        return 1

    monkeypatch.setattr(
        "app.api.v1.jobs.increment_rate_limit", fake_increment_rate_limit
    )
    monkeypatch.setattr(
        "app.api.v1.jobs.enqueue_job_analysis", lambda *_args: "task-job-1"
    )

    response = client.post(
        "/api/v1/jobs/analyze",
        json={"source": "text", "raw_text": "Python backend role"},
    )

    assert response.status_code == 202
    assert charged_tiers == ["premium"]
    assert "users" not in supabase.tables_read


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/v1/ats/optimize", {"job_id": "job-00"}),
        ("/api/v1/interview-kits", {"job_id": "job-00"}),
        ("/api/v1/interview-kits/kit-1/regenerate", None),
    ],
)
def test_premium_features_follow_the_session_plan(
    client: TestClient,
    supabase: RecordingSupabase,
    path: str,
    body: dict[str, str] | None,
) -> None:
    _log_in(supabase, session_tier="free", table_tier="premium")

    response = client.post(path, json=body)

    assert response.status_code == 403
    assert response.json()["code"] == "PREMIUM_REQUIRED"
    assert "users" not in supabase.tables_read
