from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.services.scraper import linkedin_scraper
from app.services.scraper.linkedin_scraper import scrape_company, scrape_person
from tests.fakes import FakeSupabase


class FakeBody:
    def __init__(self, text: str) -> None:
        self.text = text

    async def inner_text(self, timeout: int) -> str:
        return self.text


class FakePage:
    def __init__(self, text: str) -> None:
        self.body = FakeBody(text)

    async def goto(self, _url: str, wait_until: str, timeout: int) -> None:
        return None

    async def route(self, _pattern: str, _handler: Any) -> None:
        return None

    def locator(self, _selector: str) -> FakeBody:
        return self.body


class FakeBrowser:
    def __init__(self, text: str) -> None:
        self.text = text

    async def new_page(self, user_agent: str) -> FakePage:
        assert "Chrome" in user_agent
        return FakePage(self.text)

    async def close(self) -> None:
        return None


class FakeChromium:
    def __init__(self, text: str) -> None:
        self.text = text

    async def launch(self, headless: bool) -> FakeBrowser:
        assert headless is True
        return FakeBrowser(self.text)


class FakePlaywright:
    def __init__(self, text: str) -> None:
        self.chromium = FakeChromium(text)


class FakePlaywrightContext:
    def __init__(self, text: str) -> None:
        self.text = text

    async def __aenter__(self) -> FakePlaywright:
        return FakePlaywright(self.text)

    async def __aexit__(self, *args: Any) -> None:
        return None


def _mock_playwright(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setattr(
        linkedin_scraper,
        "async_playwright",
        lambda: FakePlaywrightContext(text),
    )
    linkedin_scraper._last_domain_request.clear()


async def _no_sleep(_seconds: float) -> None:
    return None


@pytest.mark.asyncio
async def test_scrape_company_extracts_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = FakeSupabase()
    _mock_playwright(
        monkeypatch,
        "\n".join(
            [
                "Acme AI",
                "Building intelligent hiring software",
                "Industry",
                "Software Development",
                "Company size",
                "51-200 employees",
                "Specialties",
                "Python, AI, Cloud",
                "We are hiring remote teams with ownership culture.",
            ]
        ),
    )

    result = await scrape_company(
        "https://www.linkedin.com/company/acme-ai/",
        db=fake_db,
        user_id="user-1",
        sleep=_no_sleep,
    )

    assert result["company_name"] == "Acme AI"
    assert result["industry"] == "Software Development"
    assert "python" in result["tech_mentions"]
    assert fake_db.tables["linkedin_scrape_cache"][0]["raw_data"] == result


@pytest.mark.asyncio
async def test_scrape_person_extracts_role_type_and_common_ground(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = FakeSupabase()
    _mock_playwright(
        monkeypatch,
        "\n".join(
            [
                "Jane Doe",
                "Senior Technical Recruiter at Acme",
                "Company",
                "Acme",
                "Hiring Python engineers for cloud architecture teams.",
            ]
        ),
    )

    result = await scrape_person(
        "https://linkedin.com/in/jane-doe/",
        db=fake_db,
        user_id="user-1",
        candidate_context={"skills": ["Python", "React"]},
        sleep=_no_sleep,
    )

    assert result["full_name"] == "Jane Doe"
    assert result["role_type"] == "HRBP"
    assert result["common_ground"] == ["python"]


@pytest.mark.asyncio
async def test_scrape_uses_valid_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_db = FakeSupabase()
    cached = {"company_name": "Cached Co"}
    fake_db.tables["linkedin_scrape_cache"].append(
        {
            "user_id": "user-1",
            "linkedin_url": "https://linkedin.com/company/cached",
            "raw_data": cached,
            "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        }
    )
    monkeypatch.setattr(
        linkedin_scraper,
        "async_playwright",
        lambda: (_ for _ in ()).throw(AssertionError("should not scrape")),
    )

    result = await scrape_company(
        "https://linkedin.com/company/cached",
        db=fake_db,
        user_id="user-1",
        sleep=_no_sleep,
    )

    assert result == cached


@pytest.mark.asyncio
async def test_scrape_returns_fallback_on_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = FakeSupabase()
    _mock_playwright(monkeypatch, "Sign in to view this private profile")

    result = await scrape_person(
        "https://linkedin.com/in/private",
        db=fake_db,
        user_id="user-1",
        sleep=_no_sleep,
    )

    assert result["scraping_failed"] is True
    assert "linkedin_authwall" in result["reason"]
