from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser
from app.services.account_deletion import (
    capture_exception,
    delete_storage_prefix,
    invalidate_user_redis,
)

router = APIRouter(prefix="/users", tags=["users"])


async def _execute(query: Any) -> Any:
    response = await query.execute()
    return getattr(response, "data", None)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> None:
    async def best_effort(step: Any) -> None:
        try:
            await step()
        except Exception as exc:
            capture_exception(exc)

    async def delete_storage() -> None:
        await delete_storage_prefix(supabase, current_user.id)

    async def invalidate_redis() -> None:
        await invalidate_user_redis(current_user.id)

    async def delete_linkedin_cache() -> None:
        await _execute(
            supabase.table("linkedin_scrape_cache")
            .delete()
            .eq("user_id", current_user.id)
        )

    async def delete_public_user() -> None:
        await _execute(supabase.table("users").delete().eq("id", current_user.id))

    async def delete_auth_user() -> None:
        await supabase.auth.admin.delete_user(current_user.supabase_uid)

    await best_effort(delete_storage)
    await best_effort(invalidate_redis)
    await best_effort(delete_linkedin_cache)
    await best_effort(delete_public_user)
    await best_effort(delete_auth_user)
