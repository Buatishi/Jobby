"""Reutilización del cliente de Supabase por event loop."""

import asyncio
from typing import Any

import pytest

from app import database


@pytest.fixture
def created(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    clients: list[object] = []

    async def fake_create(_url: str, _key: str) -> Any:
        client = object()
        clients.append(client)
        return client

    monkeypatch.setattr(database, "create_async_client", fake_create)
    monkeypatch.setattr(
        database, "_get_supabase_credentials", lambda: ("https://x.supabase.co", "k")
    )
    monkeypatch.setattr(database, "_clients", database.weakref.WeakKeyDictionary())
    return clients


def test_the_same_loop_reuses_one_client(created: list[object]) -> None:
    async def twice() -> tuple[object, object]:
        first = await database.get_supabase_client()
        return first, await database.get_supabase_client()

    first, second = asyncio.run(twice())

    assert first is second
    assert len(created) == 1


def test_each_loop_gets_its_own_client(created: list[object]) -> None:
    """Las tareas locales corren con asyncio.run en otro hilo: no comparten cliente."""
    first = asyncio.run(database.get_supabase_client())
    second = asyncio.run(database.get_supabase_client())

    assert first is not second
    assert len(created) == 2


def test_missing_configuration_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(database, "_get_supabase_credentials", lambda: ("", ""))

    with pytest.raises(RuntimeError, match="Missing Supabase service configuration"):
        asyncio.run(database.get_supabase_client())
