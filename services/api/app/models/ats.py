from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


class ATSKeywordMatch(BaseModel):
    keyword: str
    status: Literal["literal", "semantic", "missing"]
    matched_text: str | None = None
    # «nice»: el aviso la presenta como deseable y vale la mitad (Decisión 42). Un
    # reporte guardado antes de esto no lo trae y se lee como obligatoria.
    priority: Literal["required", "nice"] = "required"


class ATSFormatIssue(BaseModel):
    code: str
    message: str
    penalty: int


class ATSRequirement(BaseModel):
    """Un requisito del puesto contra lo que muestra la persona (Decisión 42).

    `ratio` es cuánto se cumple (0 a 1) y entra en el puntaje. Superar lo pedido cuenta
    como cumplido (1) y solo deja una `note`: no suma ni resta.
    """

    key: str
    label: str
    required: str
    actual: str
    status: Literal["met", "partial", "unmet"]
    ratio: float
    note: str | None = None
    # El requisito se dedujo del nivel del puesto («Senior»), no lo dice el aviso.
    estimated: bool = False
    # Qué se tuvo en cuenta, para que la persona pueda comprobarlo.
    detail: list[str] = Field(default_factory=list)


class ATSReport(BaseModel):
    job_id: str
    ats_score: int
    keyword_matches: list[ATSKeywordMatch]
    format_issues: list[ATSFormatIssue]
    # Años, formación e idiomas que pide el puesto. Vacío si el aviso no pide nada de
    # eso o si el reporte es anterior a este análisis.
    requirements: list[ATSRequirement] = Field(default_factory=list)
    # False cuando el CV principal no tiene banderas de formato (se leyó antes de que
    # existieran): `format_issues` vacío significa entonces «no se miró», no «sin
    # problemas».
    format_evaluated: bool = True


class ATSOptimizeRequest(BaseModel):
    job_id: str
    # Palabras del reporte que la persona declara saber aunque ni su CV ni su LinkedIn
    # lo muestren (Decisión 24). Solo valen las que el reporte da por faltantes.
    confirmed_keywords: list[Annotated[str, StringConstraints(max_length=80)]] = Field(
        default_factory=list, max_length=30
    )


class OptimizedCVSection(BaseModel):
    section_name: str
    original_excerpt: str
    rewritten_text: str
    added_keywords: list[str]
    rationale: str
    # Keywords que el texto nuevo menciona sin respaldo en el CV:
    # la persona las confirma antes de usarlas.
    unverified_keywords: list[str] = Field(default_factory=list)
    # Keywords que el reporte daba por faltantes pero el CV respalda con otras palabras
    # («casos de prueba» para «testing»): el texto nuevo las escribe y cuentan.
    backed_keywords: list[str] = Field(default_factory=list)
    # Keywords que la persona declaró saber sin que el CV las respalde: el texto nuevo
    # las escribe y cuentan, pero se muestran aparte porque las responde ella.
    declared_keywords: list[str] = Field(default_factory=list)
    # A qué experiencia del CV corresponde una sección `experiences` (Decisión 24).
    # La IA devuelve el fragmento como un registro («cargo | empresa | fechas…») y no
    # como el texto de una viñeta, así que no se puede ubicar por el texto.
    target_id: str = ""
    target_company: str = ""
    target_title: str = ""


class ATSOptimizeResponse(BaseModel):
    job_id: str
    sections: list[OptimizedCVSection]
    ats_score_before: int | None = None
    ats_score_after: int | None = None
