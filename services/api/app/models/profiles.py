from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MasterProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    user_id: str
    headline: str | None = None
    summary: str | None = None
    target_role: str | None = None
    target_seniority: str | None = None
    work_modality: str | None = None
    target_industry: list[str] | None = None
    linkedin_url: str | None = None
    completeness_pct: int = 0
    inferred_soft_skills: list[str] = Field(default_factory=list)
    soft_skills_computed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class MasterProfileUpdate(BaseModel):
    headline: str | None = None
    summary: str | None = None
    target_role: str | None = None
    target_seniority: str | None = None
    work_modality: str | None = None
    target_industry: list[str] | None = None
    linkedin_url: str | None = None

    def to_update_payload(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)
