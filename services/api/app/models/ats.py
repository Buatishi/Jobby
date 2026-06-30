from typing import Literal

from pydantic import BaseModel


class ATSKeywordMatch(BaseModel):
    keyword: str
    status: Literal["literal", "semantic", "missing"]
    matched_text: str | None = None


class ATSFormatIssue(BaseModel):
    code: str
    message: str
    penalty: int


class ATSReport(BaseModel):
    job_id: str
    ats_score: int
    keyword_matches: list[ATSKeywordMatch]
    format_issues: list[ATSFormatIssue]


class ATSOptimizeRequest(BaseModel):
    job_id: str


class OptimizedCVSection(BaseModel):
    section_name: str
    original_excerpt: str
    rewritten_text: str
    added_keywords: list[str]
    rationale: str


class ATSOptimizeResponse(BaseModel):
    job_id: str
    sections: list[OptimizedCVSection]
