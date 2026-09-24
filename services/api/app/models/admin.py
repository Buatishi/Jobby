"""Métricas de administración: solo conteos y promedios, nunca datos de una persona.

Los modelos filtran la respuesta: si la función de la base devolviera un campo más, no
llega al cliente.
"""

from datetime import date, datetime

from pydantic import BaseModel


class UserMetrics(BaseModel):
    total: int
    free: int
    premium: int
    new_last_7_days: int
    new_last_30_days: int


class CvMetrics(BaseModel):
    total: int
    done: int
    failed: int
    in_progress: int


class JobMetrics(BaseModel):
    total: int
    last_7_days: int


class MatchMetrics(BaseModel):
    total: int
    last_7_days: int
    average_score: int | None
    rated: int
    average_rating: float | None


class InterviewKitMetrics(BaseModel):
    total: int
    done: int
    failed: int


class DailyActivity(BaseModel):
    day: date
    cvs: int
    jobs: int
    matches: int


class AdminMetrics(BaseModel):
    generated_at: datetime
    users: UserMetrics
    cvs: CvMetrics
    jobs: JobMetrics
    matches: MatchMetrics
    interview_kits: InterviewKitMetrics
    daily_activity: list[DailyActivity]
