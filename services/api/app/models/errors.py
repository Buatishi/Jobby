from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str
    code: str
    details: dict[str, Any] = Field(default_factory=dict)
