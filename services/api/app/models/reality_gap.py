from typing import Literal

from pydantic import BaseModel


class RealityGapSkill(BaseModel):
    skill_id: str | None = None
    name: str
    category: str | None = None
    # `None` cuando el documento falta o todavía no se leyó: no hay con qué comparar.
    in_cv: bool | None = None
    in_linkedin: bool | None = None
    # Falso en una skill que solo nombra un documento (por ejemplo, solo LinkedIn).
    saved: bool
    confirmed: bool
    rejected: bool
    coherence_score: int | None = None
    recommendation: str | None = None


class RealityGapDocument(BaseModel):
    filename: str | None = None
    uploaded_at: str | None = None
    status: str | None = None
    # «document»: las skills salen de lo que dijo el documento. «saved»: es un CV leído
    # antes de guardar su lista propia y se usan las marcas de las skills guardadas.
    skills_source: Literal["document", "saved"] | None = None


class RealityGapSummary(BaseModel):
    comparable: bool
    total: int
    in_both: int
    only_cv: int
    only_linkedin: int
    in_neither: int
    score: int | None = None


class RealityGapReport(BaseModel):
    profile_id: str
    skills: list[RealityGapSkill]
    summary: RealityGapSummary
    cv: RealityGapDocument | None = None
    linkedin: RealityGapDocument | None = None
