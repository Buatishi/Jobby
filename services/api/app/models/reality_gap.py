from pydantic import BaseModel


class RealityGapSkill(BaseModel):
    skill_id: str | None = None
    name: str
    category: str | None = None
    in_cv: bool
    in_linkedin: bool
    rejected: bool
    coherence_score: int
    recommendation: str | None = None


class RealityGapReport(BaseModel):
    profile_id: str
    skills: list[RealityGapSkill]
