from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Los mismos valores que entiende el cálculo del MatchScore (s_seniority y s_company):
# editar a otro texto dejaría el puesto con un valor que la fórmula ignora.
JobSeniority = Literal["junior", "mid", "senior", "staff", "principal"]
JobModality = Literal["remote", "hybrid", "onsite"]
JobText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
JobSalary = Annotated[int, Field(ge=0, le=100_000_000)]
JobCurrency = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class JobAnalysisRequest(BaseModel):
    source: Literal["url", "text"]
    url: str | None = Field(default=None, max_length=2048)
    raw_text: str | None = Field(default=None, max_length=30_000)


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


class JobUpdateRequest(BaseModel):
    """Datos editables de un puesto (Decisión 1).

    El texto original y la URL no se aceptan: cambiarlos exigiría volver a analizar el
    puesto con IA. Un campo enviado como null se borra; uno que no se envía no cambia.
    """

    model_config = ConfigDict(extra="forbid")

    job_title: JobText | None = None
    company_name: JobText | None = None
    required_seniority: JobSeniority | None = None
    required_modality: JobModality | None = None
    salary_min: JobSalary | None = None
    salary_max: JobSalary | None = None
    currency: JobCurrency | None = None


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
