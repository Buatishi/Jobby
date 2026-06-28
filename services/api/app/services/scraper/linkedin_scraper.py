import asyncio
import random
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse, urlunparse

from app.database import get_supabase_client

try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - tests mock Playwright.
    PlaywrightTimeoutError = TimeoutError
    async_playwright = None

_last_domain_request: dict[str, float] = {}


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", "", ""))


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


async def _get_cached(
    db: Any,
    user_id: str,
    normalized_url: str,
) -> dict[str, Any] | None:
    data = await _execute(
        db.table("linkedin_scrape_cache")
        .select("*")
        .eq("user_id", user_id)
        .eq("linkedin_url", normalized_url)
        .single()
    )
    if not isinstance(data, dict):
        return None

    expires_at = _parse_datetime(data.get("expires_at"))
    raw_data = data.get("raw_data")
    if expires_at and expires_at > _now() and isinstance(raw_data, dict):
        return raw_data
    return None


async def _set_cached(
    db: Any,
    user_id: str,
    normalized_url: str,
    raw_data: dict[str, Any],
) -> None:
    await _execute(
        db.table("linkedin_scrape_cache").upsert(
            {
                "user_id": user_id,
                "linkedin_url": normalized_url,
                "raw_data": raw_data,
                "scraped_at": _now().isoformat(),
                "expires_at": (_now() + timedelta(days=7)).isoformat(),
            }
        )
    )


async def _respect_domain_delay(url: str, sleep: Any = asyncio.sleep) -> None:
    domain = urlparse(url).netloc.lower()
    current = asyncio.get_running_loop().time()
    previous = _last_domain_request.get(domain)
    if previous is not None:
        delay = random.uniform(2.0, 5.0)
        elapsed = current - previous
        if elapsed < delay:
            await sleep(delay - elapsed)
    _last_domain_request[domain] = asyncio.get_running_loop().time()


def _blocked_reason(text: str) -> str | None:
    lowered = text.lower()
    if any(marker in lowered for marker in ("authwall", "sign in", "join linkedin")):
        return "linkedin_authwall"
    if any(marker in lowered for marker in ("private profile", "unavailable")):
        return "private_or_unavailable"
    if any(marker in lowered for marker in ("cloudflare", "captcha", "blocked")):
        return "blocked"
    return None


async def _scrape_text(url: str, sleep: Any = asyncio.sleep) -> str:
    if async_playwright is None:
        raise RuntimeError("playwright_not_available")

    await _respect_domain_delay(url, sleep)
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page(user_agent=user_agent)
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                text = await page.locator("body").inner_text(timeout=30_000)
            finally:
                await browser.close()
    except PlaywrightTimeoutError as exc:
        raise RuntimeError("timeout") from exc

    text = str(text).strip()
    reason = _blocked_reason(text)
    if reason:
        raise RuntimeError(reason)
    return text


def _line_after(label: str, lines: list[str]) -> str | None:
    lowered_label = label.lower()
    for index, line in enumerate(lines):
        if lowered_label in line.lower() and index + 1 < len(lines):
            return lines[index + 1]
    return None


def _themes(text: str) -> list[str]:
    candidates = (
        "hiring",
        "ai",
        "data",
        "remote",
        "culture",
        "growth",
        "product",
        "security",
        "cloud",
    )
    lowered = text.lower()
    return [candidate for candidate in candidates if candidate in lowered]


def _tech_mentions(text: str) -> list[str]:
    technologies = (
        "python",
        "java",
        "react",
        "typescript",
        "aws",
        "gcp",
        "azure",
        "kubernetes",
        "postgres",
        "redis",
        "ai",
        "machine learning",
    )
    lowered = text.lower()
    return sorted({tech for tech in technologies if tech in lowered})


def _culture_signals(text: str) -> list[str]:
    signals = (
        "remote",
        "hybrid",
        "diversity",
        "inclusion",
        "learning",
        "ownership",
        "collaboration",
        "innovation",
    )
    lowered = text.lower()
    return sorted({signal for signal in signals if signal in lowered})


def _parse_company(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    company_name = lines[0] if lines else None
    industry = _line_after("industry", lines)
    company_size = _line_after("company size", lines) or _line_after("employees", lines)
    specialties_line = _line_after("specialties", lines)
    specialties = (
        [item.strip() for item in re.split(r",|·|\|", specialties_line) if item.strip()]
        if specialties_line
        else []
    )
    description = " ".join(lines[1:8]) if len(lines) > 1 else None

    return {
        "company_name": company_name,
        "tagline": lines[1] if len(lines) > 1 else None,
        "description": description,
        "industry": industry,
        "company_size": company_size,
        "specialties": specialties,
        "recent_posts_themes": _themes(text),
        "tech_mentions": _tech_mentions(text),
        "culture_signals": _culture_signals(text),
    }


def _infer_role_type(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("cto", "ceo", "founder", "chief")):
        return "C-Level"
    if any(token in lowered for token in ("recruiter", "talent", "hrbp", "people")):
        return "HRBP"
    if any(token in lowered for token in ("engineer", "technical", "architect", "dev")):
        return "Technical"
    return "Hiring Manager"


def _seniority_signals(text: str) -> list[str]:
    signals = ("lead", "manager", "director", "head", "senior", "principal", "chief")
    lowered = text.lower()
    return [signal for signal in signals if signal in lowered]


def _likely_priorities(text: str) -> list[str]:
    priorities = {
        "hiring": ("hiring", "talent", "recruiting"),
        "technical_quality": ("architecture", "scalability", "security", "quality"),
        "delivery": ("delivery", "roadmap", "launch", "growth"),
        "culture": ("culture", "people", "collaboration", "team"),
    }
    lowered = text.lower()
    return [
        name
        for name, keywords in priorities.items()
        if any(keyword in lowered for keyword in keywords)
    ]


def _parse_person(
    text: str,
    candidate_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    full_name = lines[0] if lines else None
    headline = lines[1] if len(lines) > 1 else None
    current_role = _line_after("current role", lines) or headline
    current_company = _line_after("company", lines)
    candidate_terms = {
        str(item).lower()
        for item in (candidate_context or {}).get("skills", [])
        if str(item).strip()
    }
    common_ground = sorted(term for term in candidate_terms if term in text.lower())

    return {
        "full_name": full_name,
        "headline": headline,
        "current_role": current_role,
        "current_company": current_company,
        "background_summary": " ".join(lines[1:8]) if len(lines) > 1 else None,
        "seniority_signals": _seniority_signals(text),
        "likely_priorities": _likely_priorities(text),
        "common_ground": common_ground,
        "role_type": _infer_role_type(text),
    }


async def scrape_company(
    url: str,
    db: Any | None = None,
    user_id: str = "system",
    sleep: Any = asyncio.sleep,
) -> dict[str, Any]:
    normalized_url = _normalize_url(url)
    db_client = db or await get_supabase_client()
    cached = await _get_cached(db_client, user_id, normalized_url)
    if cached is not None:
        return cached

    try:
        text = await _scrape_text(normalized_url, sleep=sleep)
        data = _parse_company(text)
    except Exception as exc:
        data = {"scraping_failed": True, "reason": str(exc)}

    await _set_cached(db_client, user_id, normalized_url, data)
    return data


async def scrape_person(
    url: str,
    db: Any | None = None,
    user_id: str = "system",
    candidate_context: dict[str, Any] | None = None,
    sleep: Any = asyncio.sleep,
) -> dict[str, Any]:
    normalized_url = _normalize_url(url)
    db_client = db or await get_supabase_client()
    cached = await _get_cached(db_client, user_id, normalized_url)
    if cached is not None:
        return cached

    try:
        text = await _scrape_text(normalized_url, sleep=sleep)
        data = _parse_person(text, candidate_context)
    except Exception as exc:
        data = {"scraping_failed": True, "reason": str(exc)}

    await _set_cached(db_client, user_id, normalized_url, data)
    return data
