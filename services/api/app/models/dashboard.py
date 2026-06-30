from pydantic import BaseModel, ConfigDict


class DashboardMatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    job_id: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    match_score: int | None = None
    created_at: str | None = None


class DashboardSummary(BaseModel):
    user_name: str | None = None
    employability_score: int | None = None
    completeness_pct: int
    missing_tip: str | None = None
    pending_analyses_count: int
    latest_matches: list[DashboardMatch]
