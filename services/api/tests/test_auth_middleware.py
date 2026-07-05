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
