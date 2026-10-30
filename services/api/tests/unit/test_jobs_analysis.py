import asyncio
import json
import threading
from typing import Any

import pytest
from fastapi.testclient import TestClient
from playwright.async_api import Error as PlaywrightError

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


def _job_json(**overrides: Any) -> str:
    base: dict[str, Any] = {
        "job_title": "Conversational AI Engineer",
        "company_name": "Acme",
        "required_seniority": "senior",
        "required_modality": "hybrid",
        "industry": "Tech",
        "tech_stack": ["Python"],
        "required_skills": ["LLMs"],
        "soft_skills": ["Autonomía"],
        "required_education": "Grado",
        "required_languages": ["Inglés"],
        "salary_min": None,
        "salary_max": None,
        "currency": None,
    }
    return json.dumps({**base, **overrides})


def test_parse_structured_job_keeps_the_expected_shape() -> None:
    job = analysis._parse_structured_job(_job_json())

    assert job.tech_stack == ["Python"]
    assert job.required_languages == ["Inglés"]
    assert job.salary_min is None


@pytest.mark.parametrize(
    ("overrides", "field", "expected"),
    [
        ({"tech_stack": None}, "tech_stack", []),
        ({"soft_skills": None}, "soft_skills", []),
        ({"required_skills": "Python, LLMs; Docker"}, "required_skills",
         ["Python", "LLMs", "Docker"]),
        ({"required_skills": [{"name": "LLMs", "level": "alto"}, "Python", None]},
         "required_skills", ["LLMs", "Python"]),
        ({"tech_stack": ["Python", 3, "", " FastAPI "]}, "tech_stack",
         ["Python", "3", "FastAPI"]),
        ({"required_education": ["Grado", "Posgrado"]}, "required_education",
         "Grado, Posgrado"),
        ({"required_education": ""}, "required_education", None),
        ({"job_title": 123}, "job_title", "123"),
        ({"required_languages": None}, "required_languages", []),
        ({"required_languages": "Inglés avanzado"}, "required_languages",
         ["Inglés avanzado"]),
    ],
)
def test_parse_structured_job_accepts_shapes_the_ai_returns(
    overrides: dict[str, Any], field: str, expected: Any
) -> None:
    job = analysis._parse_structured_job(_job_json(**overrides))

    assert getattr(job, field) == expected


def test_parse_structured_job_keeps_the_language_level_the_match_reads() -> None:
    job = analysis._parse_structured_job(
        _job_json(
            required_languages=[
                {"language": "Inglés", "level": "avanzado"},
                {"name": "Portugués"},
                {"nivel": "B2"},
                "Español nativo",
            ]
        )
    )

    # El objeto sin nombre se descarta; el resto conserva el nivel que haya.
    assert job.required_languages == [
        {"name": "Inglés", "level": "avanzado"},
        {"name": "Portugués"},
        "Español nativo",
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (1500000, 1500000),
        (1500000.0, 1500000),
        (2500.6, 2501),
        ("1500000", 1500000),
        ("1.500.000", 1500000),
        ("1,500,000", 1500000),
        ("$ 1.500.000 ARS", 1500000),
        ("1500,60", 1501),
        ("1000-2000", None),
        ("1.500.000 - 2.000.000", None),
        ("3k", None),
        ("a convenir", None),
        ("", None),
        (-5, None),
        (True, None),
        (10**10, None),
        (10**400, None),
        (float("nan"), None),
        (float("inf"), None),
        ([1500000], None),
        (None, None),
    ],
)
def test_parse_structured_job_reads_the_salary_or_leaves_it_empty(
    raw: Any, expected: int | None
) -> None:
    job = analysis._parse_structured_job(_job_json(salary_min=raw, salary_max=raw))

    assert job.salary_min == expected
    assert job.salary_max == expected


def test_parse_structured_job_logs_the_failing_field_without_the_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level("WARNING", logger="jobmatch.tasks"):
        with pytest.raises(ValueError, match="failed validation"):
            analysis._parse_structured_job('["texto-privado-del-aviso"]')

    assert "root:model_type" in caplog.text
    assert "texto-privado-del-aviso" not in caplog.text


def test_parse_structured_job_rejects_json_that_is_not_json() -> None:
    with pytest.raises(ValueError, match="invalid job JSON"):
        analysis._parse_structured_job("no es json")


class MessyGateway(FakeGateway):
    """Respuesta como la de un aviso real que quedó sin analizar: forma distinta."""

    async def generate(
        self,
        _task_type: str,
        _user_tier: str,
        _prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        return _job_json(
            tech_stack=None,
            required_skills=[{"name": "Agentes conversacionales"}],
            required_languages=[{"language": "Inglés", "level": "avanzado"}],
            required_education=["Grado en sistemas"],
            salary_min="1.500.000",
            salary_max=2500000.0,
        )


@pytest.mark.asyncio
async def test_run_job_analysis_saves_a_job_the_ai_described_loosely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = FakeSupabase()
    monkeypatch.setattr(analysis, "enqueue_match", lambda *args: "match-task-1")

    result = await analysis.run_job_analysis(
        "job-2",
        "user-1",
        "text",
        None,
        "Conversational AI role, híbrido en CABA",
        supabase=fake_supabase,
        gateway=MessyGateway(),  # type: ignore[arg-type]
    )

    assert result["id"] == "job-2"
    saved = fake_supabase.tables["job_descriptions"][0]
    assert saved["tech_stack"] == []
    assert saved["required_skills"] == ["Agentes conversacionales"]
    assert saved["required_languages"] == [{"name": "Inglés", "level": "avanzado"}]
    assert saved["required_education"] == "Grado en sistemas"
    assert (saved["salary_min"], saved["salary_max"]) == (1500000, 2500000)


class FakeBody:
    def __init__(self, text: str, should_timeout: bool = False) -> None:
        self.text = text
        self.should_timeout = should_timeout

    async def inner_text(self, timeout: int) -> str:
        if self.should_timeout:
            raise TimeoutError("timeout")
        return self.text


JOB_TEXT = "Backend role. " * 30  # un aviso de verdad pasa de los 200 caracteres


class FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status


class Overlap:
    """Cuenta cuántas páginas están abiertas a la vez (también entre hilos)."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.current = 0
        self.peak = 0


class FakePage:
    def __init__(
        self,
        text: str,
        should_timeout: bool = False,
        *,
        status: int = 200,
        url: str = "https://example.com/job",
        overlap: Overlap | None = None,
    ) -> None:
        self.body = FakeBody(text, should_timeout)
        self.status = status
        self.url = url
        self.overlap = overlap

    async def goto(self, _url: str, wait_until: str, timeout: int) -> FakeResponse:
        if self.body.should_timeout:
            raise TimeoutError("timeout")
        if self.overlap is not None:
            with self.overlap.lock:
                self.overlap.current += 1
                self.overlap.peak = max(self.overlap.peak, self.overlap.current)
            try:
                await asyncio.sleep(0.05)
            finally:
                with self.overlap.lock:
                    self.overlap.current -= 1
        return FakeResponse(self.status)

    async def route(self, _pattern: str, _handler: Any) -> None:
        return None

    def locator(self, _selector: str) -> FakeBody:
        return self.body


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    async def route_web_socket(self, _pattern: str, _handler: Any) -> None:
        return None

    async def new_page(self) -> FakePage:
        return self.page


class FakeBrowser:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    async def new_context(self, user_agent: str, service_workers: str) -> FakeContext:
        assert "Chrome" in user_agent
        assert service_workers == "block"
        return FakeContext(self.page)

    async def close(self) -> None:
        return None


class FakeChromium:
    def __init__(self, page: FakePage, launch_error: Exception | None = None) -> None:
        self.page = page
        self.launch_error = launch_error

    async def launch(self, headless: bool, proxy: dict[str, str]) -> FakeBrowser:
        assert headless is True
        assert proxy["server"].startswith("http://127.0.0.1:")
        if self.launch_error is not None:
            raise self.launch_error
        return FakeBrowser(self.page)


class FakePlaywright:
    def __init__(self, page: FakePage, launch_error: Exception | None = None) -> None:
        self.chromium = FakeChromium(page, launch_error)


class FakePlaywrightContext:
    def __init__(self, page: FakePage, launch_error: Exception | None = None) -> None:
        self.page = page
        self.launch_error = launch_error

    async def __aenter__(self) -> FakePlaywright:
        return FakePlaywright(self.page, self.launch_error)

    async def __aexit__(self, *args: Any) -> None:
        return None


@pytest.mark.asyncio
async def test_scrape_url_returns_body_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.scraper.playwright_scraper.async_playwright",
        lambda: FakePlaywrightContext(FakePage(JOB_TEXT)),
    )

    assert await scrape_url("https://example.com/job") == JOB_TEXT.strip()


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


def _use_fake_browser(
    monkeypatch: pytest.MonkeyPatch,
    make_page: Any,
    launch_error: Exception | None = None,
) -> None:
    async def public(url: str) -> str:
        # La guarda de URL tiene sus tests en test_url_guard.py; acá no se consulta DNS.
        return url

    monkeypatch.setattr(playwright_scraper, "ensure_public_http_url", public)
    monkeypatch.setattr(
        "app.services.scraper.playwright_scraper.async_playwright",
        lambda: FakePlaywrightContext(make_page(), launch_error),
    )


async def _blocked_reason(url: str = "https://example.com/job") -> str:
    with pytest.raises(ScraperBlockedError) as exc:
        await scrape_url(url)
    return str(exc.value.reason)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 429, 999])
async def test_scrape_url_treats_a_status_that_rejects_bots_as_blocked(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    _use_fake_browser(monkeypatch, lambda: FakePage(JOB_TEXT, status=status))

    assert await _blocked_reason() == "authwall"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "final_url",
    [
        "https://www.linkedin.com/authwall?trk=bf",
        "https://www.linkedin.com/uas/login?session_redirect=x",
        "https://example.com/login",
    ],
)
async def test_scrape_url_treats_a_redirect_to_a_login_page_as_blocked(
    monkeypatch: pytest.MonkeyPatch, final_url: str
) -> None:
    # El texto es largo a propósito: lo que decide es la dirección a la que se llegó.
    _use_fake_browser(monkeypatch, lambda: FakePage(JOB_TEXT, url=final_url))

    assert await _blocked_reason() == "authwall"


@pytest.mark.asyncio
async def test_scrape_url_reads_a_job_whose_url_only_contains_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://example.com/careers/login-engineer/123"
    _use_fake_browser(monkeypatch, lambda: FakePage(JOB_TEXT, url=url))

    assert await scrape_url(url) == JOB_TEXT.strip()


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", "   \n  ", "Sign in", "x" * 199])
async def test_scrape_url_treats_an_almost_empty_page_as_blocked(
    monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    _use_fake_browser(monkeypatch, lambda: FakePage(text))

    assert await _blocked_reason() == "empty"


@pytest.mark.asyncio
async def test_scrape_url_still_detects_the_cloudflare_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_fake_browser(
        monkeypatch, lambda: FakePage("Checking your browser before access. " * 10)
    )

    assert await _blocked_reason() == "cloudflare"


@pytest.mark.asyncio
async def test_scrape_url_asks_for_the_text_when_the_browser_cannot_start(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    error = PlaywrightError(
        "BrowserType.launch: Executable doesn't exist at /x/chrome\n"
        "╔════════════╗\n║ playwright install ║\n╚════════════╝"
    )
    _use_fake_browser(monkeypatch, lambda: FakePage(JOB_TEXT), launch_error=error)

    with caplog.at_level("WARNING", logger="jobmatch.scraper"):
        reason = await _blocked_reason()

    assert reason == "browser"
    # El motivo queda en el log, solo la primera línea (sin el recuadro de ayuda).
    assert "Executable doesn't exist at /x/chrome" in caplog.text
    assert "╔" not in caplog.text


@pytest.mark.asyncio
async def test_scrape_url_opens_one_browser_at_a_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    overlap = Overlap()
    _use_fake_browser(monkeypatch, lambda: FakePage(JOB_TEXT, overlap=overlap))

    results = await asyncio.gather(
        *(scrape_url("https://example.com/job") for _ in range(3))
    )

    assert results == [JOB_TEXT.strip()] * 3
    assert overlap.peak == 1


def test_scrape_url_opens_one_browser_at_a_time_across_task_threads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Las tareas locales corren cada una en su hilo y con su propio ciclo de eventos.
    overlap = Overlap()
    _use_fake_browser(monkeypatch, lambda: FakePage(JOB_TEXT, overlap=overlap))
    results: list[str] = []

    def run() -> None:
        results.append(asyncio.run(scrape_url("https://example.com/job")))

    threads = [threading.Thread(target=run) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert results == [JOB_TEXT.strip()] * 3
    assert overlap.peak == 1


@pytest.mark.asyncio
async def test_scrape_url_gives_up_when_the_browser_stays_busy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    overlap = Overlap()
    _use_fake_browser(monkeypatch, lambda: FakePage(JOB_TEXT, overlap=overlap))
    monkeypatch.setattr(playwright_scraper, "BROWSER_SLOT_WAIT_SECONDS", 0.3)
    assert playwright_scraper._BROWSER_SLOT.acquire(blocking=False)

    try:
        assert await _blocked_reason() == "timeout"
    finally:
        playwright_scraper._BROWSER_SLOT.release()

    assert overlap.peak == 0  # no llegó a abrir otro navegador


@pytest.mark.asyncio
async def test_scrape_url_frees_the_browser_slot_after_a_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(playwright_scraper, "PlaywrightTimeoutError", TimeoutError)
    # Si el permiso quedara tomado, el segundo intento esperaría y fallaría por tiempo.
    monkeypatch.setattr(playwright_scraper, "BROWSER_SLOT_WAIT_SECONDS", 0.3)
    _use_fake_browser(monkeypatch, lambda: FakePage("", should_timeout=True))
    assert await _blocked_reason() == "timeout"

    _use_fake_browser(monkeypatch, lambda: FakePage(JOB_TEXT))

    assert await scrape_url("https://example.com/job") == JOB_TEXT.strip()
