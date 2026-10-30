import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

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


# La IA no siempre respeta la forma pedida (una lista en null, un idioma como objeto,
# un sueldo con puntos de miles). Cada valor se lleva a la forma de la tabla antes de
# validar: un aviso válido no debe fallar por cómo vino escrito el JSON.
_TEXT_KEYS = ("name", "skill", "title", "value", "text", "label")
_LANGUAGE_NAME_KEYS = ("name", "language", "idioma")
_LANGUAGE_LEVEL_KEYS = ("level", "nivel", "proficiency")
_LIST_SEPARATORS = re.compile(r"[,;\n]")
_NUMBER_TOKEN = re.compile(r"\d[\d.,]*")
_THOUSANDS = re.compile(r"^\d{1,3}(?:[.,]\d{3})+$")
_DECIMALS = re.compile(r"^\d+[.,]\d{1,2}$")
_SCALED = re.compile(r"\d\s*[kKmM]\b")
_MAX_INT4 = 2_147_483_647  # salary_min y salary_max son INTEGER en la base


def _text(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        return ", ".join(text for item in value if (text := _text(item))) or None
    if isinstance(value, dict):
        return next(
            (text for key in _TEXT_KEYS if (text := _text(value.get(key)))), None
        )
    return None


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return _LIST_SEPARATORS.split(value)
    return value if isinstance(value, list) else [value]


def _text_list(value: Any) -> list[str]:
    return [text for item in _items(value) if (text := _text(item))]


def _language_list(value: Any) -> list[str | dict[str, str]]:
    languages: list[str | dict[str, str]] = []
    for item in _items(value):
        if not isinstance(item, dict):
            if text := _text(item):
                languages.append(text)
            continue
        # El MatchScore lee {"name", "level"}: el nivel pedido se conserva.
        name = next((t for k in _LANGUAGE_NAME_KEYS if (t := _text(item.get(k)))), None)
        if name is None:
            continue
        level = next(
            (t for k in _LANGUAGE_LEVEL_KEYS if (t := _text(item.get(k)))), None
        )
        languages.append({"name": name, "level": level} if level else {"name": name})
    return languages


def _salary(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    number: float
    if isinstance(value, int | float):
        number = value
    elif isinstance(value, str):
        tokens = _NUMBER_TOKEN.findall(value)
        # Un rango («1000-2000») o una abreviatura («3k») no tienen un único valor.
        if len(tokens) != 1 or _SCALED.search(value):
            return None
        token = tokens[0]
        if _THOUSANDS.match(token):
            number = float(re.sub(r"[.,]", "", token))
        elif _DECIMALS.match(token):
            number = float(token.replace(",", "."))
        elif token.isdigit():
            number = float(token)
        else:
            return None
    else:
        return None
    # NaN e infinito también quedan fuera: ninguna comparación con ellos es verdadera.
    if not 0 <= number <= _MAX_INT4:
        return None
    return round(number)


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
    required_languages: list[str | dict[str, str]] = Field(default_factory=list)
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None

    @field_validator(
        "job_title",
        "company_name",
        "required_seniority",
        "required_modality",
        "industry",
        "required_education",
        "currency",
        mode="before",
    )
    @classmethod
    def coerce_text(cls, value: Any) -> str | None:
        return _text(value)

    @field_validator("tech_stack", "required_skills", "soft_skills", mode="before")
    @classmethod
    def coerce_text_list(cls, value: Any) -> list[str]:
        return _text_list(value)

    @field_validator("required_languages", mode="before")
    @classmethod
    def coerce_languages(cls, value: Any) -> list[str | dict[str, str]]:
        return _language_list(value)

    @field_validator("salary_min", "salary_max", mode="before")
    @classmethod
    def coerce_salary(cls, value: Any) -> int | None:
        return _salary(value)
