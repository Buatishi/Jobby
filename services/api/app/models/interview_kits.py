from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CompatibilityArea(BaseModel):
    name: str
    score: int = Field(ge=0, le=100)
    notes: str


class Strength(BaseModel):
    title: str
    evidence: str


class Risk(BaseModel):
    title: str
    mitigation: str


class ModelAnswer(BaseModel):
    question: str
    answer: str
    evaluation_criteria: list[str] = Field(default_factory=list)


class ActionPlan(BaseModel):
    title: str
    steps: list[str] = Field(default_factory=list)


class InterviewKitContent(BaseModel):
    overall_summary: str
    compatibility_areas: list[CompatibilityArea] = Field(default_factory=list)
    strengths: list[Strength] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    argumentario: list[str] = Field(default_factory=list)
    model_answers: list[ModelAnswer] = Field(default_factory=list)
    candidate_questions: list[str] = Field(default_factory=list)
    action_plan: ActionPlan | None = None


class InterviewKitCreate(BaseModel):
    job_id: str
    match_id: str | None = None
    company_linkedin_url: str | None = Field(default=None, max_length=2048)
    interviewer_linkedin_url: str | None = Field(default=None, max_length=2048)
    interviewer_name: str | None = Field(default=None, max_length=200)
    interviewer_role: str | None = Field(default=None, max_length=200)


class InterviewKitRatingUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)


class InterviewKit(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    user_id: str
    profile_id: str
    job_id: str
    match_id: str | None = None
    title: str | None = None
    questions: dict[str, Any] | None = None
    prep_notes: dict[str, Any] | None = None
    status: str = "pending"
    error_msg: str | None = None
    user_rating: int | None = None
    ai_model_used: str | None = None
    task_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
