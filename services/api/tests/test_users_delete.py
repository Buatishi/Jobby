
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from tests.fakes import FakeRedis, FakeSupabase


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1",
        supabase_uid="auth-user-1",
        email="person@example.com",
    )


def test_delete_current_user_removes_records_files_and_caches(
    client: TestClient,
    fake_redis: FakeRedis,
) -> None:
    fake_supabase = FakeSupabase()
    fake_redis.values.update(
        {
            "rate:jobs:user-1:2026-06": "1",
            "rate:ats:user-1:2026-06-01": "3",
            "rate:jobs:user-2:2026-06": "1",
        }
    )
    fake_supabase.tables["linkedin_scrape_cache"].append(
        {
            "id": "cache-1",
            "user_id": "user-1",
            "linkedin_url": "https://linkedin.com/in/person",
        }
    )
    # Los archivos viven bajo el uid de Supabase Auth (así los sube el frontend).
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "doc-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "storage_path": "auth-user-1/cv.pdf",
        }
    )
    fake_supabase.tables["skills"].append(
        {"id": "skill-1", "profile_id": "profile-1", "name": "Python"}
    )
    fake_supabase.storage.files["auth-user-1/cv.pdf"] = b"%PDF-1.4 fake"
    fake_supabase.storage.files["auth-user-1/nested/old.pdf"] = b"%PDF-1.4 fake"
    fake_supabase.storage.files["auth-user-2/cv.pdf"] = b"%PDF-1.4 fake"

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.delete("/api/v1/users/me")

    assert response.status_code == 204
    assert fake_supabase.tables["users"] == []
    assert fake_supabase.tables["master_profiles"] == []
    assert fake_supabase.tables["uploaded_documents"] == []
    assert fake_supabase.tables["skills"] == []
    assert fake_supabase.tables["linkedin_scrape_cache"] == []
    assert fake_supabase.storage.files == {"auth-user-2/cv.pdf": b"%PDF-1.4 fake"}
    # La baja borra solo los contadores de esta persona, con la función real.
    assert fake_redis.values == {"rate:jobs:user-2:2026-06": "1"}
    assert fake_supabase.auth.admin.deleted_users == ["auth-user-1"]


def test_delete_current_user_uses_the_real_cv_bucket_and_registered_paths(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()
    # Ruta registrada en la base que no cuelga de la carpeta del uid.
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "doc-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "storage_path": "legacy/old-cv.pdf",
        }
    )
    fake_supabase.storage.files["legacy/old-cv.pdf"] = b"%PDF-1.4 fake"
    fake_supabase.storage.files["auth-user-2/cv.pdf"] = b"%PDF-1.4 fake"

    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client

    response = client.delete("/api/v1/users/me")

    assert response.status_code == 204
    # Regresión: antes se vaciaba el bucket huérfano "cv-docs" y los CV quedaban.
    assert fake_supabase.storage.requested_buckets == {"cv-documents"}
    assert fake_supabase.storage.files == {"auth-user-2/cv.pdf": b"%PDF-1.4 fake"}
