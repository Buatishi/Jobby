"""El ATS mide habilidades reales del aviso y las busca por palabra completa.

Decisión 35. Antes la IA recibía la orden de incluir «seniority, idiomas y títulos
requeridos», así que el reporte pedía «Junior», «Full time», «Buenos Aires» o el título
del puesto como si fueran habilidades, y todo eso bajaba el puntaje. Además la búsqueda
era por texto contenido: «Git» aparecía en «Digital» y «SQL» en «PostgreSQL».
"""

import json
from typing import Any

import pytest

from app.services.ats_analyzer.keyword_matcher import analyze_keywords
from app.services.skill_filter import skill_keywords

JOB_TITLE = "Desarrollador/a Backend Python Jr"


class _Gateway:
    """Devuelve las palabras clave dadas; cada texto distinto tiene su propio vector.

    Así lo que no coincide por texto tampoco coincide por significado.
    """

    def __init__(self, keywords: list[str]) -> None:
        self.keywords = keywords
        self.prompts: list[str] = []
        self.axes: dict[str, int] = {}

    async def generate(
        self,
        _task_type: str,
        _user_tier: str,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        self.prompts.append(prompt)
        return json.dumps({"keywords": self.keywords})

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            axis = self.axes.setdefault(text.lower(), len(self.axes))
            vectors.append([1.0 if axis == position else 0.0 for position in range(64)])
        return vectors


def _cv(skills: list[str], experience: str = "") -> dict[str, Any]:
    parsed: dict[str, Any] = {"skills": [{"name": name} for name in skills]}
    if experience:
        parsed["experiences"] = [{"title": "Analista", "description": experience}]
    return {"parsed_data": parsed}


async def _statuses(keywords: list[str], cv: dict[str, Any]) -> dict[str, str]:
    result = await analyze_keywords(
        {}, cv, gateway=_Gateway(keywords), keywords=keywords  # type: ignore[arg-type]
    )
    return {match.keyword: match.status for match in result.matches}


# --- qué cuenta como habilidad --------------------------------------------------------


@pytest.mark.parametrize(
    "term",
    [
        "Junior",
        "Jr",
        "Senior",
        "Semi Senior",
        "SSR",
        "Trainee",
        "Pasante",
        "Nivel junior",
    ],
)
def test_the_seniority_is_not_a_skill(term: str) -> None:
    assert skill_keywords([term, "Python"], {}) == ["Python"]


@pytest.mark.parametrize(
    "term",
    [
        "Remoto",
        "Híbrido",
        "Hybrid",
        "Presencial",
        "Home Office",
        "Full time",
        "Full-Time",
        "Part time",
        "Jornada completa",
        "Tiempo completo",
    ],
)
def test_the_modality_and_the_working_hours_are_not_skills(term: str) -> None:
    assert skill_keywords([term, "Python"], {}) == ["Python"]


@pytest.mark.parametrize(
    "term", ["Buenos Aires", "CABA", "Córdoba", "Argentina", "LATAM", "Capital Federal"]
)
def test_a_city_or_a_country_is_not_a_skill(term: str) -> None:
    assert skill_keywords([term, "Python"], {}) == ["Python"]


def test_the_title_of_the_job_is_not_a_skill_but_a_skill_inside_it_is() -> None:
    job = {"job_title": JOB_TITLE}

    kept = skill_keywords(
        [JOB_TITLE.upper(), "desarrollador/a backend python jr", "Python"], job
    )

    assert kept == ["Python"]


def test_the_feminine_forms_of_the_modality_are_not_skills() -> None:
    assert skill_keywords(["Modalidad híbrida", "Remota", "Docker"], {}) == ["Docker"]


def test_what_the_job_says_about_its_level_and_modality_is_not_a_skill() -> None:
    """El nivel y la modalidad del puesto son texto libre y suelen traer el lugar:
    «Híbrida (presencial en Vicente López, CABA/Zona Norte GBA)»."""
    job = {
        "required_seniority": "Junior (mínimo 1 año de experiencia)",
        "required_modality": (
            "Híbrida (presencial en Vicente López, CABA/Zona Norte GBA)"
        ),
    }

    kept = skill_keywords(
        ["Vicente López", "Zona Norte GBA", "Presencial", "Junior", "Git", "Linux"], job
    )

    assert kept == ["Git", "Linux"]


def test_a_skill_that_only_shares_a_word_with_the_job_data_is_kept() -> None:
    job = {"required_modality": "Híbrida", "company_name": "Empresa de Prueba SRL"}

    assert skill_keywords(["Power BI", "Testing", "Empresa de Prueba SRL"], job) == [
        "Power BI",
        "Testing",
    ]


def test_a_task_written_as_a_sentence_is_not_a_skill() -> None:
    sentences = [
        "Escritura de consultas SQL y mantenimiento de base de datos",
        "Integración de servicios de terceros mediante APIs",
        "Desarrollo y mantenimiento de APIs REST",
    ]

    assert skill_keywords([*sentences, "SQL"], {}) == ["SQL"]


def test_the_real_skills_stay_as_they_came_and_in_order() -> None:
    skills = [
        "Python",
        "React",
        "SQL",
        "Git",
        "API REST",
        "Power BI",
        "C++",
        "Node.js",
        "Inglés",
        "Scrum",
        "Gestión de proyectos",
        "Revisiones de código",
    ]

    assert skill_keywords(skills, {"job_title": "Analista de datos"}) == skills


def test_a_repeated_skill_counts_once() -> None:
    assert skill_keywords(["Python", "python", "Python "], {}) == ["Python"]


# --- palabra completa -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_git_is_not_found_inside_digital() -> None:
    cv = _cv(["Python"], experience="Operado y Analista Digital en una pyme")

    assert await _statuses(["Git"], cv) == {"Git": "missing"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("keyword", "cv_term"),
    [
        ("SQL", "PostgreSQL"),
        ("Java", "JavaScript"),
        ("Go", "Django"),
        ("C", "C++"),
        ("Script", "TypeScript"),
    ],
)
async def test_a_skill_is_not_found_inside_another_one(
    keyword: str, cv_term: str
) -> None:
    assert await _statuses([keyword], _cv([cv_term])) == {keyword: "missing"}


@pytest.mark.asyncio
async def test_a_whole_word_is_found_in_a_skill_a_sentence_or_a_list() -> None:
    cv = _cv(
        ["REST API", "C++ y C#"],
        experience="Automaticé facturas con Python, Excel y Salesforce.",
    )

    keywords = ["API", "Python", "Salesforce", "C++", "C#", "Excel"]
    statuses = await _statuses(keywords, cv)

    assert set(statuses.values()) == {"literal"}


@pytest.mark.asyncio
async def test_the_match_ignores_the_case() -> None:
    assert await _statuses(["GIT"], _cv(["git"])) == {"GIT": "literal"}


@pytest.mark.asyncio
async def test_the_dots_of_a_name_belong_to_it_but_a_full_stop_does_not() -> None:
    cv = _cv([], experience="Usé Node.js. También Python.")

    assert await _statuses(["Node.js", "Python"], cv) == {
        "Node.js": "literal",
        "Python": "literal",
    }


# --- qué se le pide a la IA y qué se guarda -------------------------------------------


@pytest.mark.asyncio
async def test_the_ai_is_asked_for_skills_and_told_what_to_leave_out() -> None:
    gateway = _Gateway(["Python"])

    await analyze_keywords(
        {"job_title": JOB_TITLE, "raw_text": "Buscamos backend"},
        _cv(["Python"]),
        gateway=gateway,  # type: ignore[arg-type]
    )

    prompt = gateway.prompts[0].lower()
    for left_out in ("título", "nivel", "modalidad", "jornada", "ciudad", "tareas"):
        assert left_out in prompt
    assert "seniority, idiomas y títulos" not in prompt


@pytest.mark.asyncio
async def test_what_the_ai_returns_is_filtered_before_the_report_uses_it() -> None:
    not_skills = ["Junior", "Buenos Aires", "Híbrido", "Full time", JOB_TITLE]
    gateway = _Gateway(["Python", *not_skills, "Docker"])

    result = await analyze_keywords(
        {"job_title": JOB_TITLE},
        _cv(["Python"]),
        gateway=gateway,  # type: ignore[arg-type]
    )

    assert result.keywords == ["Docker", "Python"]
    assert [match.keyword for match in result.matches] == ["Docker", "Python"]


@pytest.mark.asyncio
async def test_keywords_saved_by_an_old_report_are_filtered_without_the_ai() -> None:
    gateway = _Gateway(["otra", "cosa"])

    result = await analyze_keywords(
        {"job_title": JOB_TITLE},
        _cv(["Python"]),
        gateway=gateway,  # type: ignore[arg-type]
        keywords=["Python", "Junior", "Remoto", "Buenos Aires", JOB_TITLE],
    )

    assert gateway.prompts == []
    assert result.keywords == ["Python"]
