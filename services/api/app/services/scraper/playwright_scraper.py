from typing import Literal

try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - local tests mock Playwright.
    PlaywrightTimeoutError = TimeoutError
    async_playwright = None

ScraperBlockedReason = Literal["timeout", "cloudflare", "paywall"]


class ScraperBlockedError(Exception):
    def __init__(self, reason: ScraperBlockedReason) -> None:
        self.reason = reason
        super().__init__(reason)


def _detect_block_reason(text: str) -> ScraperBlockedReason | None:
    lowered = text.lower()
    cloudflare_markers = (
        "cloudflare",
        "checking your browser",
        "attention required",
        "cf-ray",
    )
    paywall_markers = (
        "paywall",
        "subscribe to continue",
        "subscription required",
        "sign in to continue",
    )

    if any(marker in lowered for marker in cloudflare_markers):
        return "cloudflare"
    if any(marker in lowered for marker in paywall_markers):
        return "paywall"
    return None


async def scrape_url(url: str) -> str:
    if async_playwright is None:
        raise ScraperBlockedError("timeout")

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
        raise ScraperBlockedError("timeout") from exc

    block_reason = _detect_block_reason(text)
    if block_reason is not None:
        raise ScraperBlockedError(block_reason)

    return str(text).strip()
