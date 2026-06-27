from pydantic import BaseModel


class CurrentUser(BaseModel):
    id: str
    supabase_uid: str
    email: str | None = None
