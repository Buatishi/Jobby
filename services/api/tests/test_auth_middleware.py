import jwt
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.config import settings
from app.database import get_supabase_client
from app.dependencies import validate_jwt
from app.main import app
from tests.fakes import FakeSupabase


async def _valid_claims() -> dict[str, str]:
    return {"sub": "auth-user-1", "email": "person@example.com"}


async def _fake_supabase() -> FakeSupabase:
    return FakeSupabase()


def test_valid_token_injects_current_user(client: TestClient) -> None:
    app.dependency_overrides[validate_jwt] = _valid_claims
    app.dependency_overrides[get_supabase_client] = _fake_supabase

    response = client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == "user-1"


def test_valid_token_provisions_missing_public_user(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["users"] = []
    fake_supabase.tables["master_profiles"] = []

    async def new_user_claims() -> dict[str, object]:
        return {
            "sub": "auth-user-2",
            "email": "new@example.com",
            "user_metadata": {"full_name": "New User"},
        }

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[validate_jwt] = new_user_claims
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert fake_supabase.tables["users"][0]["supabase_uid"] == "auth-user-2"
    assert fake_supabase.tables["users"][0]["email"] == "new@example.com"
    assert fake_supabase.tables["users"][0]["full_name"] == "New User"
    assert fake_supabase.tables["master_profiles"][0]["user_id"] == "users-1"


def test_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": "Token inválido",
        "code": "UNAUTHORIZED",
        "details": {},
    }


async def test_hs256_supabase_token_uses_jwt_secret(
    monkeypatch,
) -> None:
    secret = "jwt-secret-with-at-least-thirty-two-bytes"
    monkeypatch.setattr(settings, "supabase_jwt_secret", secret)
    token = jwt.encode(
        {"sub": "auth-user-1", "aud": "authenticated"},
        secret,
        algorithm="HS256",
    )

    claims = await validate_jwt(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        settings,
    )

    assert claims["sub"] == "auth-user-1"


async def test_token_falls_back_to_supabase_auth_user(
    monkeypatch,
) -> None:
    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, str]:
            return {"id": "auth-user-1", "email": "person@example.com"}

    class FakeAsyncClient:
        def __init__(self, **_: object) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            pass

        async def get(self, *_: object, **__: object) -> FakeResponse:
            return FakeResponse()

    token = jwt.encode(
        {"sub": "auth-user-1", "aud": "authenticated"},
        "real-secret-with-at-least-thirty-two-bytes",
        algorithm="HS256",
    )
    monkeypatch.setattr(
        settings,
        "supabase_jwt_secret",
        "wrong-secret-with-at-least-thirty-two-bytes",
    )
    monkeypatch.setattr(settings, "supabase_anon_key", "anon-key")
    monkeypatch.setattr("app.dependencies.httpx.AsyncClient", FakeAsyncClient)

    claims = await validate_jwt(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        settings,
    )

    assert claims["sub"] == "auth-user-1"
    assert claims["email"] == "person@example.com"
