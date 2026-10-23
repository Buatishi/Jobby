"""Alias y traducciones en el MatchScore y en el ATS.

Caso medido en producción (puesto «Desarrollador/a Full Stack Jr»): el puesto pide «API
REST» y el perfil tiene «REST APIs». La comparación literal las trataba como distintas,
las skills quedaron en 5 de 6 y el puesto figuraba con «git» como faltante, que la
persona sí tiene. Ahora el MatchScore y el ATS comparan con `canonical_skill_key`, la
misma regla que ya usa el marcado de LinkedIn.

Lo que se fija acá:
- un alias o una traducción cuenta como coincidencia literal;
- lo parecido pero distinto («Java» y «JavaScript», «React» y «React Native») no;
- el puntaje solo puede subir respecto de la comparación literal anterior;
- la lista de skills faltantes nombra las que de verdad faltan.
"""

import json
from typing import Any

import pytest

from app.services.ats_analyzer.keyword_matcher import analyze_keywords
from app.services.match_engine.common import normalize_text
from app.services.match_engine.s_company import compute_company_score
from app.services.match_engine.s_skills import (
    compute_skills_score,
    required_skill_names,
)


def _skills(*names: str, **extra: Any) -> list[dict[str, Any]]:
    return [{"name": name, **extra} for name in names]


def _job(*required: str, tech: list[str] | None = None) -> dict[str, Any]:
    return {"required_skills": list(required), "tech_stack": tech or []}


# --- skills del MatchScore --------------------------------------------------------


def test_the_case_measured_in_production_scores_six_of_six() -> None:
    job = _job("Python", "JavaScript", "React", "SQL", "API REST", "Git")
    profile = _skills("Python", "JavaScript", "React", "SQL", "REST APIs", "Git")

    result = compute_skills_score(profile, job)

    assert result["score"] == 1.0
    assert result["missing_skills"] == []
    assert len(result["literal_hits"]) == 6


@pytest.mark.parametrize(
    ("required", "saved"),
    [
        ("API REST", "REST APIs"),
        ("React.js", "React"),
        ("React", "ReactJS"),
        ("Node", "Node.js"),
        ("Integración de APIs", "API Integrations"),
        ("API Integrations", "Integración de APIs"),
        ("Gestión de proyectos", "Project Management"),
        ("Trabajo en equipo", "Teamwork"),
        ("Postgres", "PostgreSQL"),
        ("Power BI", "Microsoft Power BI"),
        ("JS", "JavaScript"),
        ("Automatización", "Automation"),
        ("Comunicación", "Communication Skills"),
    ],
)
def test_an_alias_or_translation_of_a_required_skill_is_a_literal_hit(
    required: str, saved: str
) -> None:
    result = compute_skills_score(_skills(saved), _job(required))

    assert result["score"] == 1.0
    assert result["literal_hits"] == [normalize_text(required)]
    assert result["missing_skills"] == []


@pytest.mark.parametrize(
    ("required", "saved"),
    [
        ("Java", "JavaScript"),
        ("JavaScript", "TypeScript"),
        ("React", "React Native"),
        ("Angular", "AngularJS"),
        ("SQL", "PostgreSQL"),
        ("Git", "GitHub"),
        ("Project Management", "Product Management"),
        ("Data Science", "Data Analysis"),
        ("Power BI", "Power Automate"),
        ("C", "C++"),
        ("Seguridad", "Ciberseguridad"),
    ],
)
def test_a_related_but_different_skill_is_not_a_hit(required: str, saved: str) -> None:
    result = compute_skills_score(_skills(saved), _job(required))

    assert result["score"] == 0.0
    assert result["literal_hits"] == []
    assert result["missing_skills"] == [normalize_text(required)]


def test_two_listings_of_the_same_skill_both_count() -> None:
    # Con alias es normal que el puesto repita una skill con dos nombres: cada una
    # cuenta, y no se divide por la cantidad de nombres distintos.
    job = _job("REST API", "API REST", "Docker", "Kubernetes")

    result = compute_skills_score(_skills("REST APIs", "Docker"), job)

    assert result["score"] == pytest.approx(3 / 4)
    assert result["missing_skills"] == ["kubernetes"]


def test_the_missing_skills_are_the_ones_that_are_missing_not_the_last_ones() -> None:
    # Antes figuraba «git» (que la persona tiene) en lugar de «api rest».
    job = _job("Python", "API REST", "Git")

    result = compute_skills_score(_skills("Python", "Git"), job)

    assert result["missing_skills"] == ["api rest"]
    assert result["literal_hits"] == ["git", "python"]


def test_a_semantic_match_is_not_listed_as_missing() -> None:
    vector_a = [1.0, 0.0, 0.0]
    vector_b = [0.0, 1.0, 0.0]
    job = {
        "required_skills": [
            {"name": "Python", "embedding": vector_a},
            {"name": "Contenedores", "embedding": vector_b},
            {"name": "Terraform", "embedding": [0.0, 0.0, 1.0]},
        ],
        "tech_stack": [],
    }
    profile = [
        {"name": "Python", "embedding": vector_a},
        {"name": "Docker", "embedding": vector_b},
    ]

    result = compute_skills_score(profile, job)

    assert result["literal_hits"] == ["python"]
    assert result["semantic_hits"] == 1
    assert result["missing_skills"] == ["terraform"]
    assert result["score"] == pytest.approx((1 + 0.6) / 3)


def test_a_job_without_required_skills_keeps_its_neutral_score() -> None:
    result = compute_skills_score(_skills("Python"), _job())

    assert result == {
        "score": 0.8,
        "literal_hits": [],
        "semantic_hits": 0,
        "missing_skills": [],
    }


def test_a_name_with_no_content_still_matches_itself() -> None:
    # «Skills» se descarta como relleno y no deja forma común: se compara como antes.
    result = compute_skills_score(_skills("Skills"), _job("skills"))

    assert result["score"] == 1.0


def _literal_score_before(profile: list[dict[str, Any]], job: dict[str, Any]) -> float:
    """El puntaje literal de antes del cambio: igualdad en minúsculas."""
    profile_names = {normalize_text(skill.get("name")) for skill in profile}
    job_names = required_skill_names(job)
    if not job_names:
        return 0.8
    return len(profile_names.intersection(job_names)) / len(job_names)


PROFILES = [
    _skills("Python", "SQL", "REST APIs", "React.js", "Git"),
    _skills("python", "sql", "docker"),
    _skills("Integración de APIs", "Trabajo en equipo", "Excel"),
    _skills("Java", "Spring", "PostgreSQL"),
    [],
]
JOBS = [
    _job("Python", "SQL", "API REST", "React", "Git"),
    _job("python", "sql", "docker", "aws"),
    _job("API Integrations", "Teamwork", "Excel", "Power BI"),
    _job("Java", "JavaScript", "Postgres"),
    _job("Cocina internacional", "HACCP"),
    _job(),
]


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("job", JOBS)
def test_the_score_never_goes_down_with_aliases(
    profile: list[dict[str, Any]], job: dict[str, Any]
) -> None:
    after = compute_skills_score(profile, job)["score"]

    assert after >= _literal_score_before(profile, job) - 1e-9


# --- stack tecnológico de la compatibilidad con la empresa ----------------------


def _tech_score(profile_names: list[str], tech_stack: list[str]) -> float:
    profile_skills = _skills(*profile_names, category="technical")
    result = compute_company_score(
        {"work_modality": "remote"},
        profile_skills,
        {"tech_stack": tech_stack, "required_modality": "remote"},
    )
    return float(result["tech_score"])


def test_the_tech_stack_recognizes_aliases() -> None:
    profile = ["REST APIs", "React.js", "Postgres"]

    assert _tech_score(profile, ["API REST", "React", "PostgreSQL"]) == 1.0


def test_the_tech_stack_does_not_equate_related_technologies() -> None:
    profile = ["JavaScript", "React Native", "SQL"]

    assert _tech_score(profile, ["Java", "React", "PostgreSQL"]) == 0.0


def _tech_score_by_category(
    profile: list[tuple[str, str | None]], tech_stack: list[str]
) -> float:
    skills = [{"name": name, "category": category} for name, category in profile]
    result = compute_company_score(
        {"work_modality": "remote"},
        skills,
        {"tech_stack": tech_stack, "required_modality": "remote"},
    )
    return float(result["tech_score"])


# Las categorías que el lector de CV puso en el perfil de producción medido: ninguna
# es «technical», y el perfil tiene las 10 tecnologías del puesto.
READER_CATEGORIES = [
    ("Python", "programming"),
    ("JavaScript", "programming"),
    ("React", "frontend"),
    ("SQL", "database"),
    ("REST APIs", "api"),
    ("Git", "version control"),
    ("Salesforce", "crm"),
    ("n8n", "automation"),
    ("Zapier", "automation"),
    ("Docker", "devops"),
    ("Liderazgo", "soft skills"),
]
PRODUCTION_STACK = [
    "Python", "JavaScript", "React", "SQL", "API REST", "Git",
    "Salesforce", "n8n", "Zapier", "Docker",
]  # fmt: skip


def test_the_tech_stack_does_not_depend_on_the_category_the_reader_gave() -> None:
    # Antes daba 0 porque solo se miraban las skills con categoría «technical».
    assert _tech_score_by_category(READER_CATEGORIES, PRODUCTION_STACK) == 1.0


@pytest.mark.parametrize("category", ["technical", "programming", "soft", "", None])
def test_the_name_decides_not_the_category_label(category: str | None) -> None:
    assert _tech_score_by_category([("Docker", category)], ["Docker"]) == 1.0


def test_a_stack_item_the_person_does_not_have_still_counts_against() -> None:
    profile = [("Python", "programming"), ("Docker", "devops")]
    stack = ["Python", "Docker", "Kubernetes", "AWS"]

    assert _tech_score_by_category(profile, stack) == 0.5


def test_the_tech_stack_does_not_equate_related_technologies_in_any_category() -> None:
    profile = [("JavaScript", "programming"), ("React Native", "mobile")]

    assert _tech_score_by_category(profile, ["Java", "React"]) == 0.0


def test_a_job_without_tech_stack_keeps_its_neutral_tech_score() -> None:
    assert _tech_score(["Python"], []) == 0.8


# --- palabras clave del ATS -----------------------------------------------------


class _Gateway:
    """Devuelve las palabras clave dadas; cada texto distinto tiene su propio vector."""

    def __init__(self, keywords: list[str]) -> None:
        self.keywords = keywords
        self.batches: list[list[str]] = []
        self.axes: dict[str, int] = {}

    async def generate(
        self,
        _task_type: str,
        _user_tier: str,
        _prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        return json.dumps({"keywords": self.keywords})

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        self.batches.append(list(texts))
        vectors = []
        for text in texts:
            axis = self.axes.setdefault(text.lower(), len(self.axes))
            vectors.append([1.0 if axis == position else 0.0 for position in range(64)])
        return vectors


def _cv(*terms: str) -> dict[str, Any]:
    return {"parsed_data": {"skills": [{"name": term} for term in terms]}}


@pytest.mark.asyncio
async def test_ats_counts_an_alias_or_translation_as_literal() -> None:
    keywords = ["Integración de APIs", "React.js", "API REST", "Gestión de proyectos"]
    gateway = _Gateway(keywords)
    cv = _cv("API Integrations", "React", "REST APIs", "Project Management")

    result = await analyze_keywords({}, cv, gateway=gateway)  # type: ignore[arg-type]

    assert {match.keyword: match.status for match in result.matches} == {
        "API REST": "literal",
        "Gestión de proyectos": "literal",
        "Integración de APIs": "literal",
        "React.js": "literal",
    }
    matched = {match.keyword: match.matched_text for match in result.matches}
    assert matched["Integración de APIs"] == "API Integrations"
    assert matched["API REST"] == "REST APIs"


@pytest.mark.asyncio
async def test_ats_asks_for_no_vectors_when_the_aliases_cover_every_keyword() -> None:
    gateway = _Gateway(["Integración de APIs", "React.js"])

    cv = _cv("API Integrations", "React")

    await analyze_keywords({}, cv, gateway=gateway)  # type: ignore[arg-type]

    assert gateway.batches == []


@pytest.mark.asyncio
async def test_ats_does_not_equate_related_technologies_by_alias() -> None:
    gateway = _Gateway(["React Native", "Power BI", "Docker"])
    cv = _cv("React", "Power Automate", "Kubernetes")

    result = await analyze_keywords({}, cv, gateway=gateway)  # type: ignore[arg-type]

    assert [match.status for match in result.matches] == ["missing"] * 3
    # Lo que no coincide por alias sigue el camino de siempre: pide vectores.
    assert len(gateway.batches) == 2
