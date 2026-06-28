from typing import Any

from app.tasks.analysis import (
    enqueue_match,
    match_task,
)
from app.tasks.analysis import (
    run_match as run_analysis_match,
)


async def run_match(
    job_id: str,
    profile_id: str,
    user_id: str,
    supabase: Any | None = None,
    gateway: Any | None = None,
) -> dict[str, Any]:
    return await run_analysis_match(
        job_id,
        profile_id,
        user_id,
        supabase=supabase,
        gateway=gateway,
    )


__all__ = ["enqueue_match", "match_task", "run_match"]
