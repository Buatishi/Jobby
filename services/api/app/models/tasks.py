from typing import Any, Literal

from pydantic import BaseModel

TaskStatus = Literal["pending", "processing", "done", "failed"]


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: Any | None = None
    error: str | None = None
