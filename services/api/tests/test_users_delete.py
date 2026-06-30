from typing import Any

from fastapi.testclient import TestClient

from app.api.v1 import users
from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from tests.fakes import FakeSupabase


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


def test_delete_current_user_removes_records_files_and_caches(
    client: TestClient,
    monkeypatch: Any,
) -> None:
    fake_supabase = FakeSupabase()
    redis_keys = {
        "ai_cache:job:user-1": "cached",
        "rate:jobs:user-1:2026-06": "1",
        "rate:jobs:user-2:2026-06": "1",
    }
    fake_supabase.tables["linkedin_scrape_cache"].append(
        {
            "id": "cache-1",
            "user_id": "user-1",
            "linkedin_url": "https://linkedin.com/in/person",
        }
    )
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "doc-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "storage_path": "user-1/cv.pdf",
        }
    )
    fake_supabase.tables["skills"].append(
        {"id": "skill-1", "profile_id": "profile-1", "name": "Python"}
    )
    fake_supabase.storage.files["user-1/cv.pdf"] = b"%PDF-1.4 fake"
    fake_supabase.storage.files["user-1/nested/old.pdf"] = b"%PDF-1.4 fake"
    fake_supabase.storage.files["user-2/cv.pdf"] = b"%PDF-1.4 fake"

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    async def fake_invalidate_user_redis(user_id: str) -> None:
        for key in list(redis_keys):
            if key.startswith("ai_cache:") or key.startswith(f"rate:jobs:{user_id}:"):
                redis_keys.pop(key)

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client
    monkeypatch.setattr(users, "invalidate_user_redis", fake_invalidate_user_redis)

    response = client.delete("/api/v1/users/me")

    assert response.status_code == 204
    assert fake_supabase.tables["users"] == []
    assert fake_supabase.tables["master_profiles"] == []
    assert fake_supabase.tables["uploaded_documents"] == []
    assert fake_supabase.tables["skills"] == []
    assert fake_supabase.tables["linkedin_scrape_cache"] == []
    assert fake_supabase.storage.files == {"user-2/cv.pdf": b"%PDF-1.4 fake"}
    assert redis_keys == {"rate:jobs:user-2:2026-06": "1"}
    assert fake_supabase.auth.admin.deleted_users == ["auth-user-1"]
