from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.jobs import JobDescription


class MatchRatingUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)


class MatchReport(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    user_id: str
    profile_id: str
    job_id: str
    match_score: int | None = None
    potential_score: int | None = None
    representation_score: int | None = None
    gap_origin: str | None = None
    score_breakdown: dict[str, Any] | None = None
    recommendations: list[Any] | None = None
    user_rating: int | None = None
    ai_model_used: str | None = None
    created_at: str | None = None
    job: JobDescription | None = None
