from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


def test_security_headers_are_added_to_api_responses() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "camera=()" in response.headers["Permissions-Policy"]
    assert response.headers["X-Permitted-Cross-Domain-Policies"] == "none"


def test_production_environment_detection() -> None:
    settings = Settings(ENVIRONMENT="production")

    assert settings.is_production is True
