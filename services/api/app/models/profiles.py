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


class UploadedDocumentCreate(BaseModel):
    profile_id: str
    type: str
    storage_path: str
    cv_slot: int | None = None
    is_primary: bool = False
    original_filename: str | None = None
    mime_type: str | None = None
    file_size: int | None = None


class UploadedDocument(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    user_id: str
    profile_id: str
    type: str
    cv_slot: int | None = None
    is_primary: bool = False
    storage_path: str
    original_filename: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    status: str = "pending"
    parsed_data: dict[str, Any] | None = None
    error_msg: str | None = None
    task_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SkillCreate(BaseModel):
    name: str
    category: str | None = None
    level: str | None = None
    in_cv: bool = False
    confirmed: bool = False


class RejectedSkillCreate(BaseModel):
    name: str
    source: str = "manual"
    reason: str | None = None


class ExperienceCreate(BaseModel):
    company: str
    title: str
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)


class EducationCreate(BaseModel):
    institution: str
    field_of_study: str | None = None
    degree_level: str | None = None


class LanguageCreate(BaseModel):
    name: str
    level: str | None = None
