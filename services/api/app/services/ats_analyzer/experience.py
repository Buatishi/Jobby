"""Años de experiencia directa de la persona, para el requisito «años» (Decisión 42).

Reglas del autor (2026-10-31):

- Solo cuentan los puestos de trabajo: freelance, por cuenta propia, en una pyme o en
  una empresa grande. No cuentan los cursos, la formación, los voluntariados ni los
  proyectos personales.
- De esos, solo cuenta el tiempo de experiencia **directa** con lo que pide el puesto.
  Un puesto es directo si lo que la persona hizo nombra alguna skill del aviso, si su
  cargo se parece al del aviso, o si los dos son de software/TI (un «IT Trainee» cuenta
  para un aviso de desarrollo). El resto se muestra como «no relacionado» y no suma.

Todo es determinista y sin IA. Los meses se cuentan completos (marzo a mayo son tres) y
dos puestos al mismo tiempo cuentan una sola vez.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.services.ats_analyzer.keyword_matcher import _contains_whole_word
from app.services.text_quality import STOPWORDS, fold

MAX_REQUIRED_YEARS = 20

# Años que se estiman cuando el aviso solo dice el nivel. Es una convención mía, no un
# dato del aviso: queda marcada como estimada. «Junior» no estima nada: no pide años.
YEARS_BY_SENIORITY = {"mid": 3, "middle": 3, "senior": 5, "staff": 8, "principal": 10}

_DATE = re.compile(r"^\s*(\d{4})(?:-(\d{1,2}))?")
_TOKEN = re.compile(r"[a-z0-9+#]+")

# Lo que se ve en el cargo o la empresa de algo que no es un puesto de trabajo.
_NOT_WORK = re.compile(
    r"\b(cursos?|courses?|capacitacion|formacion|bootcamp|taller|workshop|training|"
    r"voluntari\w*|volunteer\w*|estudiante|student|hobby)\b"
    r"|proyecto personal|personal project|side project"
)

_YEARS_BEFORE = re.compile(
    r"(?<![\d.])(\d{1,2})\s*\+?\s*(?:(?:-|a|to)\s*\d{1,2}\s*\+?\s*)?"
    r"(?:years?|yrs?|anos)\b[^.\n]{0,60}?\b(?:experience|experiencia)\b"
)
_YEARS_AFTER = re.compile(
    r"\b(?:experience|experiencia)\b[^.\n]{0,40}?(?<![\d.])(\d{1,2})\s*\+?\s*"
    r"(?:years?|yrs?|anos)\b"
)

# Cargos que se escriben distinto en español y en inglés.
_TITLE_ALIASES = {
    "desarrollador": "developer",
    "desarrolladora": "developer",
    "programador": "developer",
    "programadora": "developer",
    "dev": "developer",
    "analista": "analyst",
    "datos": "data",
    "disenador": "designer",
    "disenadora": "designer",
}
# Palabras que no dicen a qué se dedica la persona.
_TITLE_NOISE = STOPWORDS | {
    "sr", "ssr", "jr", "senior", "semi", "junior", "lead", "mid", "middle", "staff",
    "principal", "trainee", "freelance", "independiente", "remoto", "remote",
    "software", "specialist", "especialista", "consultant", "consultor", "associate",
    "member", "tecnico", "technical", "operador", "operator",
}  # fmt: skip


# Palabras de un cargo de software o TI. Con estas dos en el cargo del puesto de la
# persona y en el aviso, la experiencia es del mismo campo aunque el texto no nombre la
# misma skill.
_SOFTWARE_TERMS = frozenset({
    "it", "ti", "dev", "developer", "software", "devops", "sysadmin", "sre", "qa",
    "tester", "backend", "frontend", "fullstack", "stack", "sistemas", "systems",
    "automation", "automatizacion", "programmer",
})  # fmt: skip


@dataclass(frozen=True)
class Role:
    """Un puesto de la persona y si cuenta para los años pedidos."""

    label: str
    start: int | None
    end: int | None
    counted: bool
    # Por qué no cuenta; vacío si cuenta.
    reason: str = ""

    @property
    def months(self) -> int:
        if self.start is None or self.end is None:
            return 0
        return max(0, self.end - self.start + 1)


def _month_index(value: Any, *, end: bool) -> int | None:
    """Mes como número (año × 12 + mes) de `AAAA-MM` o `AAAA`; None si no es fecha."""
    if not isinstance(value, str):
        return None
    match = _DATE.match(value)
    if not match:
        return None
    year = int(match.group(1))
    if not 1950 <= year <= 2100:
        return None
    month = int(match.group(2)) if match.group(2) else (12 if end else 1)
    if not 1 <= month <= 12:
        return None
    return year * 12 + month - 1


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _tokens(text: str) -> set[str]:
    found = {_TITLE_ALIASES.get(token, token) for token in _TOKEN.findall(fold(text))}
    return {token for token in found if token not in _TITLE_NOISE and len(token) > 1}


def _skill_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names = [item.get("name") if isinstance(item, dict) else item for item in value]
    return [name.strip() for name in names if isinstance(name, str) and name.strip()]


def job_skill_names(job: dict[str, Any]) -> list[str]:
    """Las skills y tecnologías que nombra el puesto, sin repetir."""
    names = [
        *_skill_names(job.get("required_skills")),
        *_skill_names(job.get("tech_stack")),
    ]
    return list(dict.fromkeys(names))


def _experience_text(row: dict[str, Any]) -> str:
    achievements = row.get("achievements")
    parts = [_text(row.get("title")), _text(row.get("description"))]
    if isinstance(achievements, list):
        parts.extend(_text(item) for item in achievements)
    return fold(" ".join(part for part in parts if part))


def _software_terms(title: str) -> set[str]:
    found = {_TITLE_ALIASES.get(token, token) for token in _TOKEN.findall(fold(title))}
    return found & _SOFTWARE_TERMS


def _is_software_job(job: dict[str, Any]) -> bool:
    return bool(_software_terms(_text(job.get("job_title")))) or bool(
        _skill_names(job.get("tech_stack"))
    )


def _is_direct(row: dict[str, Any], job: dict[str, Any], skills: list[str]) -> bool:
    text = _experience_text(row)
    if any(_contains_whole_word(text, fold(skill)) for skill in skills):
        return True
    title = _text(row.get("title"))
    if _tokens(_text(job.get("job_title"))) & _tokens(title):
        return True
    return _is_software_job(job) and bool(_software_terms(title))


def assess_roles(
    rows: Iterable[dict[str, Any]],
    job: dict[str, Any],
    today: date | None = None,
) -> list[Role]:
    """Cada puesto de la persona con sus meses y si cuenta como experiencia directa."""
    now = today or date.today()
    current_month = now.year * 12 + now.month - 1
    skills = job_skill_names(job)
    roles: list[Role] = []
    for row in rows:
        title, company = _text(row.get("title")), _text(row.get("company"))
        label = " — ".join(part for part in (company, title) if part) or "Sin nombre"
        if _NOT_WORK.search(fold(f"{title} {company}")):
            roles.append(Role(label, None, None, False, "no es un puesto de trabajo"))
            continue

        start = _month_index(row.get("started_at"), end=False)
        end = _month_index(row.get("ended_at"), end=True)
        if row.get("is_current") is True and end is None:
            end = current_month
        if start is None:
            roles.append(Role(label, None, None, False, "sin fecha de inicio"))
        elif end is None:
            roles.append(Role(label, start, None, False, "sin fecha de fin"))
        elif end < start:
            roles.append(Role(label, start, end, False, "las fechas no cierran"))
        elif not _is_direct(row, job, skills):
            roles.append(
                Role(label, start, min(end, current_month), False,
                     "no se relaciona con lo que pide el puesto")
            )  # fmt: skip
        else:
            roles.append(Role(label, start, min(end, current_month), True))
    return roles


def direct_months(roles: Iterable[Role]) -> int:
    """Meses de experiencia directa; un mes en dos puestos cuenta una vez."""
    months: set[int] = set()
    for role in roles:
        if role.counted and role.start is not None and role.end is not None:
            months.update(range(role.start, role.end + 1))
    return len(months)


def required_years(job: dict[str, Any]) -> tuple[int | None, bool]:
    """Años que pide el puesto y si es una estimación por el nivel («Senior» → 5).

    Se toma la primera mención de años de experiencia del aviso («5+ years of
    experience», «mínimo 2 años de experiencia»). Sin ella, se estima por el nivel.
    """
    text = fold(_text(job.get("raw_text")))
    found = [
        (match.start(), int(match.group(1)))
        for pattern in (_YEARS_BEFORE, _YEARS_AFTER)
        for match in pattern.finditer(text)
        if 0 < int(match.group(1)) <= MAX_REQUIRED_YEARS
    ]
    if found:
        return min(found)[1], False
    estimated = YEARS_BY_SENIORITY.get(fold(_text(job.get("required_seniority"))))
    return (estimated, True) if estimated else (None, False)


def describe_months(months: int) -> str:
    """«6 meses», «1 año», «2 años y 3 meses»."""
    years, rest = divmod(months, 12)
    parts = []
    if years:
        parts.append(f"{years} año" + ("s" if years != 1 else ""))
    if rest or not years:
        parts.append(f"{rest} mes" + ("es" if rest != 1 else ""))
    return " y ".join(parts)
