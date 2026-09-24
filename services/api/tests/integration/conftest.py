"""Pruebas de integración contra el proyecto de Supabase de pruebas (Decisión 4).

La API corre dentro del proceso y habla con una base real (PostgreSQL, PostgREST y
Supabase Auth del proyecto de pruebas), nunca con la de producción. Sin las variables
TEST_SUPABASE_URL y TEST_SUPABASE_SERVICE_ROLE_KEY estas pruebas fallan en lugar de
saltearse: un pipeline sin la base de pruebas no puede quedar en verde.
"""

import os
import secrets
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable

import httpx
import pytest
from supabase import AsyncClient, create_async_client

from app.config import settings
from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser

CreatePerson = Callable[[], Awaitable[CurrentUser]]

MISSING_VARIABLES = (
    "Faltan TEST_SUPABASE_URL y TEST_SUPABASE_SERVICE_ROLE_KEY: las pruebas de "
    "integración solo corren contra el proyecto de Supabase de pruebas (Decisión 4). "
    'Para correr solo las unitarias: pytest -m "not integration".'
)


def _test_project_credentials() -> tuple[str, str]:
    url = os.environ.get("TEST_SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("TEST_SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        pytest.fail(MISSING_VARIABLES, pytrace=False)
    # Nunca se reutilizan las variables de producción, ni por error de configuración.
    if url == settings.supabase_url.strip().rstrip("/"):
        pytest.fail(
            "TEST_SUPABASE_URL apunta al mismo proyecto que SUPABASE_URL: las pruebas "
            "de integración no corren contra producción.",
            pytrace=False,
        )
    return url, key


@pytest.fixture()
async def database() -> AsyncClient:
    url, key = _test_project_credentials()
    return await create_async_client(url, key)


@pytest.fixture()
async def create_person(database: AsyncClient) -> AsyncIterator[CreatePerson]:
    """Crea personas reales en Supabase Auth y al terminar las borra con sus datos."""
    created: list[str] = []

    async def create() -> CurrentUser:
        response = await database.auth.admin.create_user(
            {
                "email": f"integracion-{uuid.uuid4().hex[:12]}@example.com",
                "password": secrets.token_urlsafe(24),
                "email_confirm": True,
            }
        )
        assert response.user is not None
        created.append(response.user.id)
        # El disparador de la migración 015 crea la fila de users y el perfil.
        row = (
            await database.table("users")
            .select("id,supabase_uid,email,role,tier")
            .eq("supabase_uid", response.user.id)
            .single()
            .execute()
        ).data
        return CurrentUser.model_validate(row)

    yield create

    errors: list[Exception] = []
    for supabase_uid in created:
        try:
            # users borra en cascada perfil, puestos, comparaciones y kits; la identidad
            # va después porque users la referencia sin cascada, igual que en la baja.
            await (
                database.table("users")
                .delete()
                .eq("supabase_uid", supabase_uid)
                .execute()
            )
            await database.auth.admin.delete_user(supabase_uid)
        except Exception as exc:  # se sigue con las demás y se informa al final
            errors.append(exc)
    if errors:
        raise errors[0]


@pytest.fixture()
async def person(create_person: CreatePerson) -> CurrentUser:
    return await create_person()


@pytest.fixture()
async def api(
    database: AsyncClient, person: CurrentUser
) -> AsyncIterator[httpx.AsyncClient]:
    """Cliente HTTP de la API con la sesión de `person` y la base de pruebas.

    La sesión se reemplaza porque la validación del token ya tiene sus propias pruebas;
    acá lo que se prueba es la API contra una base real.
    """

    async def current_person() -> CurrentUser:
        return person

    async def test_database() -> AsyncClient:
        return database

    app.dependency_overrides[get_current_user] = current_person
    app.dependency_overrides[get_supabase_client] = test_database
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
