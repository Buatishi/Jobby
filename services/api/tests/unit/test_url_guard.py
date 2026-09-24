from typing import Any

import pytest

from app.services.scraper import url_guard
from app.services.scraper.url_guard import (
    UnsafeUrlError,
    ensure_linkedin_host,
    ensure_public_http_url,
    make_route_guard,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/admin",
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/",
        "http://192.168.1.10/",
        "http://172.16.0.1/",
        "http://100.64.0.1/",
        "http://0.0.0.0/",
        "ftp://example.com/file",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "https://user:secret@example.com/",
        "http://example.com:6379/",
        "http://example.com:8080/",
        "http://intranet.local/",
        "http://service.internal/",
        "http://app.localhost/",
        "",
        "   ",
    ],
)
async def test_rejects_urls_that_the_server_must_not_visit(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        await ensure_public_http_url(url)


@pytest.mark.asyncio
async def test_rejects_urls_that_are_too_long() -> None:
    with pytest.raises(UnsafeUrlError):
        await ensure_public_http_url("https://example.com/" + "a" * 3000)


@pytest.mark.asyncio
async def test_rejects_a_hostname_that_resolves_to_a_private_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def resolve_private(_host: str, _port: int) -> list[str]:
        return ["10.0.0.7"]

    monkeypatch.setattr(url_guard, "_resolve", resolve_private)

    with pytest.raises(UnsafeUrlError):
        await ensure_public_http_url("https://rebinding.example.com/job")


@pytest.mark.asyncio
async def test_rejects_when_any_resolved_address_is_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def resolve_mixed(_host: str, _port: int) -> list[str]:
        return ["93.184.216.34", "127.0.0.1"]

    monkeypatch.setattr(url_guard, "_resolve", resolve_mixed)

    with pytest.raises(UnsafeUrlError):
        await ensure_public_http_url("https://mixed.example.com/")


@pytest.mark.asyncio
async def test_rejects_a_host_that_does_not_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unresolved(_host: str, _port: int) -> list[str]:
        raise UnsafeUrlError("No se pudo resolver el host de la URL.")

    monkeypatch.setattr(url_guard, "_resolve", unresolved)

    with pytest.raises(UnsafeUrlError):
        await ensure_public_http_url("https://no-existe.example.com/")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/job",
        "http://example.com/job",
        "https://example.com:443/job",
        "  https://boards.example.com/jobs/1  ",
        "https://www.linkedin.com/company/acme/",
        "http://93.184.216.34/",
    ],
)
async def test_accepts_public_web_urls(url: str) -> None:
    assert await ensure_public_http_url(url) == url.strip()


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/in/jane-doe",
        "https://linkedin.com/company/acme",
        "https://ar.linkedin.com/in/jane-doe",
    ],
)
def test_accepts_linkedin_hosts(url: str) -> None:
    ensure_linkedin_host(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/?next=linkedin.com",
        "https://notlinkedin.com/in/x",
        "https://linkedin.com.evil.com/in/x",
        "https://linkedin.com@10.0.0.1/",
        "not a url",
    ],
)
def test_rejects_hosts_that_only_look_like_linkedin(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        ensure_linkedin_host(url)


class FakeRequest:
    def __init__(self, url: str) -> None:
        self.url = url


class FakeRoute:
    def __init__(self, url: str) -> None:
        self.request = FakeRequest(url)
        self.actions: list[str] = []

    async def continue_(self) -> None:
        self.actions.append("continue")

    async def abort(self) -> None:
        self.actions.append("abort")


@pytest.mark.asyncio
async def test_route_guard_aborts_requests_to_internal_addresses() -> None:
    guard = make_route_guard()
    public = FakeRoute("https://example.com/job")
    metadata = FakeRoute("http://169.254.169.254/latest/meta-data/")
    inline = FakeRoute("data:text/plain;base64,aGk=")

    await guard(public)
    await guard(metadata)
    await guard(inline)

    assert public.actions == ["continue"]
    assert metadata.actions == ["abort"]
    assert inline.actions == ["continue"]


@pytest.mark.asyncio
async def test_route_guard_blocks_a_redirect_to_a_private_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def resolve(host: str, _port: int) -> list[str]:
        return ["10.1.2.3"] if host == "internal.example.com" else ["93.184.216.34"]

    monkeypatch.setattr(url_guard, "_resolve", resolve)
    guard = make_route_guard()
    first = FakeRoute("https://example.com/redirector")
    redirected = FakeRoute("https://internal.example.com/admin")

    await guard(first)
    await guard(redirected)

    assert first.actions == ["continue"]
    assert redirected.actions == ["abort"]


@pytest.mark.asyncio
async def test_route_guard_resolves_each_origin_only_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def resolve(host: str, _port: int) -> list[str]:
        calls.append(host)
        return ["93.184.216.34"]

    monkeypatch.setattr(url_guard, "_resolve", resolve)
    guard = make_route_guard()

    for path in ("a.js", "b.css", "c.png"):
        await guard(FakeRoute(f"https://cdn.example.com/{path}"))

    assert calls == ["cdn.example.com"]


def test_a_route_guard_type_is_awaitable() -> None:
    guard: Any = make_route_guard()

    assert callable(guard)
