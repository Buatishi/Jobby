"""Permisos por rol, leídos de la base.

La consigna (3.4) no admite comparar nombres de rol en el código: cada endpoint exige
un permiso, y qué permisos tiene cada rol es un dato de la tabla `role_permissions`.
Sumar un permiso a un rol no requiere cambiar código.
"""

from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.models.auth import CurrentUser


class Permission(StrEnum):
    METRICS_READ = "metrics:read"


async def fetch_permissions(supabase: Any, role: str) -> frozenset[str]:
    response = await (
        supabase.table("role_permissions")
        .select("permission")
        .eq("role_id", role)
        .execute()
    )
    rows = getattr(response, "data", None)
    if not isinstance(rows, list):
        return frozenset()
    return frozenset(
        str(row["permission"])
        for row in rows
        if isinstance(row, dict) and row.get("permission")
    )


def require_permission(
    permission: Permission,
) -> Callable[..., Awaitable[CurrentUser]]:
    """Dependencia que responde 403 si el rol de quien llama no tiene el permiso."""

    async def dependency(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
        supabase: Annotated[Any, Depends(get_supabase_client)],
    ) -> CurrentUser:
        if permission not in await fetch_permissions(supabase, current_user.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "No tenés permiso para esta acción",
                    "code": "FORBIDDEN",
                    "details": {},
                },
            )
        return current_user

    return dependency
