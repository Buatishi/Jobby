import asyncio
import logging
import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal
from urllib.parse import urlparse

from app.services.scraper.egress_proxy import guarded_browser
from app.services.scraper.url_guard import ensure_public_http_url, new_guarded_page

logger = logging.getLogger("jobmatch.scraper")

MAX_SCRAPED_CHARS = 60_000
# Un aviso de verdad pasa de unos cientos de caracteres. Menos que esto es una página
# que no cargó, una pantalla de acceso o una aplicación que todavía no pintó nada.
MIN_SCRAPED_CHARS = 200
# Estados con los que un sitio rechaza a un navegador automatizado (999 es el de
# LinkedIn).
BLOCKED_STATUSES = frozenset({401, 403, 429, 999})
LOGIN_SEGMENTS = frozenset({"authwall", "login", "signin", "sign-in", "checkpoint"})

# Chromium suma 150 a 250 MB a la API, que ya ocupa unos 100 de los 512 MB de Render:
# dos navegadores a la vez midieron 418 MB. Se abre uno solo por vez. Las tareas corren
# en hilos distintos, cada uno con su propio ciclo de eventos: por eso el semáforo es de
# hilos y no de asyncio.
_BROWSER_SLOT = threading.BoundedSemaphore(1)
BROWSER_SLOT_WAIT_SECONDS = 60.0
_SLOT_POLL_SECONDS = 0.25

PlaywrightTimeoutError: type[Exception]
PlaywrightError: type[Exception]
async_playwright: Any

try:
    from playwright.async_api import Error as PlaywrightError
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - local tests mock Playwright.
    PlaywrightTimeoutError = TimeoutError
    PlaywrightError = TimeoutError
    async_playwright = None

ScraperBlockedReason = Literal[
    "timeout", "cloudflare", "paywall", "authwall", "empty", "browser"
]


class ScraperBlockedError(Exception):
    def __init__(self, reason: ScraperBlockedReason) -> None:
        self.reason = reason
        super().__init__(reason)


@asynccontextmanager
async def _browser_slot() -> AsyncIterator[None]:
    # Se espera sin bloquear el ciclo de eventos y sin dejar un permiso colgado si la
    # tarea se cancela mientras espera.
    deadline = time.monotonic() + BROWSER_SLOT_WAIT_SECONDS
    while not _BROWSER_SLOT.acquire(blocking=False):
        if time.monotonic() >= deadline:
            raise ScraperBlockedError("timeout")
        await asyncio.sleep(_SLOT_POLL_SECONDS)
    try:
        yield
    finally:
        _BROWSER_SLOT.release()


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


def _is_login_page(final_url: str) -> bool:
    # Por segmento y no por texto: «/careers/login-engineer» es un aviso, no un acceso.
    segments = urlparse(final_url).path.lower().split("/")
    return any(segment in LOGIN_SEGMENTS for segment in segments)


async def _read_page_text(url: str, user_agent: str) -> str:
    try:
        async with async_playwright() as playwright:
            async with guarded_browser(playwright) as browser:
                page = await new_guarded_page(browser, user_agent)
                response = await page.goto(
                    url, wait_until="domcontentloaded", timeout=30_000
                )
                if response is not None and response.status in BLOCKED_STATUSES:
                    raise ScraperBlockedError("authwall")
                # Un sitio que pide iniciar sesión redirige a su pantalla de acceso.
                if _is_login_page(page.url):
                    raise ScraperBlockedError("authwall")
                return str(await page.locator("body").inner_text(timeout=30_000))
    except PlaywrightTimeoutError as exc:
        raise ScraperBlockedError("timeout") from exc
    except PlaywrightError as exc:
        # El navegador no arrancó (falta en la imagen) o se cayó (por ejemplo, sin
        # memoria). La persona recibe el aviso de pegar el texto; el motivo queda en el
        # log, solo la primera línea porque Playwright agrega un recuadro de ayuda.
        detail = (str(exc).splitlines() or [""])[0][:200]
        logger.warning(
            "El navegador del scraper falló: %s: %s", type(exc).__name__, detail
        )
        raise ScraperBlockedError("browser") from exc


async def scrape_url(url: str) -> str:
    if async_playwright is None:
        raise ScraperBlockedError("timeout")

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )

    safe_url = await ensure_public_http_url(url)

    async with _browser_slot():
        text = (await _read_page_text(safe_url, user_agent)).strip()

    block_reason = _detect_block_reason(text)
    if block_reason is not None:
        raise ScraperBlockedError(block_reason)
    if len(text) < MIN_SCRAPED_CHARS:
        raise ScraperBlockedError("empty")

    return text[:MAX_SCRAPED_CHARS]
