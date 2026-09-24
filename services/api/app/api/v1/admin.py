from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.permissions import Permission, require_permission
from app.database import get_supabase_client
from app.models.admin import AdminMetrics
from app.models.auth import CurrentUser

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", response_model=AdminMetrics)
async def get_admin_metrics(
    _admin: Annotated[
        CurrentUser, Depends(require_permission(Permission.METRICS_READ))
    ],
    supabase: Annotated[Any, Depends(get_supabase_client)],
) -> AdminMetrics:
    # Una sola consulta agregada en la base (función admin_metrics, migración 026).
    response = await supabase.rpc("admin_metrics", {}).execute()
    data = getattr(response, "data", None)
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "No se pudieron calcular las métricas",
                "code": "METRICS_UNAVAILABLE",
                "details": {},
            },
        )
    return AdminMetrics.model_validate(data)
