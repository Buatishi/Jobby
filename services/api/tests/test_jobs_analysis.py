import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.scraper import playwright_scraper
from app.services.scraper.playwright_scraper import ScraperBlockedError, scrape_url
from app.tasks import analysis
from tests.fakes import FakeSupabase


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


class FakeGateway:
    async def generate(
        self,
        _task_type: str,
        _user_tier: str,
        _prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        return json.dumps(
            {
                "job_title": "Backend Engineer",
                "company_name": "Acme",
                "tech_stack": ["Python", "FastAPI"],
                "required_skills": ["Python", "FastAPI"],
                "soft_skills": ["communication"],
            }
        )

    async def embed(self, _text: str) -> list[float]:
        return [0.2] * 1536


def test_analyze_job_requires_minimum_profile_confidence(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["master_profiles"][0]["completeness_pct"] = 59

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.post(
        "/api/v1/jobs/analyze",
        json={"source": "text", "raw_text": "Python backend role"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "PROFILE_INCOMPLETE"


@pytest.mark.parametrize(
    ("completeness_pct", "expected_confidence"),
    [(60, "medium"), (85, "high")],
)
def test_analyze_job_enqueues_task_for_allowed_profile(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    completeness_pct: int,
    expected_confidence: str,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["master_profiles"][0]["completeness_pct"] = completeness_pct
    enqueued: list[tuple[str, str, str, str | None, str | None]] = []

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    def fake_enqueue(
        job_id: str,
        user_id: str,
        source: str,
        url: str | None,
        raw_text: str | None,
    ) -> str:
        enqueued.append((job_id, user_id, source, url, raw_text))
        return "task-job-1"

    async def fake_increment_rate_limit(*args: Any, **kwargs: Any) -> int:
        return 1

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    monkeypatch.setattr("app.api.v1.jobs.enqueue_job_analysis", fake_enqueue)
    monkeypatch.setattr(
        "app.api.v1.jobs.increment_rate_limit",
        fake_increment_rate_limit,
    )

    response = client.post(
        "/api/v1/jobs/analyze",
        json={"source": "text", "raw_text": "Python backend role"},
    )

    assert response.status_code == 202
    assert response.json()["task_id"] == "task-job-1"
    assert response.json()["profile_confidence"] == expected_confidence
    assert enqueued[0][1:] == ("user-1", "text", None, "Python backend role")


@pytest.mark.asyncio
async def test_run_job_analysis_saves_job_and_enqueues_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    enqueued_matches: list[tuple[str, str, str]] = []

    def fake_enqueue_match(job_id: str, profile_id: str, user_id: str) -> str:
        enqueued_matches.append((job_id, profile_id, user_id))
        return "match-task-1"

    monkeypatch.setattr(analysis, "enqueue_match", fake_enqueue_match)

    result = await analysis.run_job_analysis(
        "job-1",
        "user-1",
        "text",
        None,
        "Python FastAPI backend role",
        supabase=fake_supabase,
        gateway=FakeGateway(),  # type: ignore[arg-type]
    )

    assert result["id"] == "job-1"
    assert result["job_title"] == "Backend Engineer"
    assert fake_supabase.tables["job_descriptions"][0]["embedding"] == [0.2] * 1536
    assert enqueued_matches == [("job-1", "profile-1", "user-1")]


class FakeBody:
    def __init__(self, text: str, should_timeout: bool = False) -> None:
        self.text = text
        self.should_timeout = should_timeout

    async def inner_text(self, timeout: int) -> str:
        if self.should_timeout:
            raise TimeoutError("timeout")
        return self.text


class FakePage:
    def __init__(self, text: str, should_timeout: bool = False) -> None:
        self.body = FakeBody(text, should_timeout)

    async def goto(self, _url: str, wait_until: str, timeout: int) -> None:
        if self.body.should_timeout:
            raise TimeoutError("timeout")

    async def route(self, _pattern: str, _handler: Any) -> None:
        return None

    def locator(self, _selector: str) -> FakeBody:
        return self.body


class FakeBrowser:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    async def new_page(self, user_agent: str) -> FakePage:
        assert "Chrome" in user_agent
        return self.page

    async def close(self) -> None:
        return None


class FakeChromium:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    async def launch(self, headless: bool) -> FakeBrowser:
        assert headless is True
        return FakeBrowser(self.page)


class FakePlaywright:
    def __init__(self, page: FakePage) -> None:
        self.chromium = FakeChromium(page)


class FakePlaywrightContext:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    async def __aenter__(self) -> FakePlaywright:
        return FakePlaywright(self.page)

    async def __aexit__(self, *args: Any) -> None:
        return None


@pytest.mark.asyncio
async def test_scrape_url_returns_body_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.scraper.playwright_scraper.async_playwright",
        lambda: FakePlaywrightContext(FakePage("Backend role")),
    )

    assert await scrape_url("https://example.com/job") == "Backend role"


@pytest.mark.asyncio
async def test_scrape_url_raises_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(playwright_scraper, "PlaywrightTimeoutError", TimeoutError)
    monkeypatch.setattr(
        "app.services.scraper.playwright_scraper.async_playwright",
        lambda: FakePlaywrightContext(FakePage("", should_timeout=True)),
    )

    with pytest.raises(ScraperBlockedError) as exc:
        await scrape_url("https://example.com/job")

    assert exc.value.reason == "timeout"
