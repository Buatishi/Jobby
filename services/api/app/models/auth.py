from pydantic import BaseModel


class CurrentUser(BaseModel):
    id: str
    supabase_uid: str
    email: str | None = None
    # Rol (permisos) y plan (cobro) son ejes independientes; no se mezclan.
    role: str = "user"
    tier: str = "free"


class CurrentUserProfile(BaseModel):
    id: str
    email: str | None
    role: str
    tier: str
    permissions: list[str]
