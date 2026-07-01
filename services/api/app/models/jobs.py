from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class JobAnalysisRequest(BaseModel):
    source: Literal["url", "text"]
    url: str | None = None
    raw_text: str | None = None


class JobAnalyzeResponse(BaseModel):
    job_id: str
    task_id: str
    profile_confidence: Literal["high", "medium"]


class JobDescription(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    user_id: str
    source_url: str | None = None
    raw_text: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    required_seniority: str | None = None
    required_modality: str | None = None
    industry: str | None = None
    tech_stack: list[str] | None = None
    required_skills: Any | None = None
    soft_skills: list[str] | None = None
    required_education: str | None = None
    required_languages: Any | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    created_at: str | None = None


class StructuredJobDescription(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_title: str | None = None
    company_name: str | None = None
    required_seniority: str | None = None
    required_modality: str | None = None
    industry: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    required_education: str | None = None
    required_languages: list[str] = Field(default_factory=list)
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
