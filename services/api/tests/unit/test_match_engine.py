import pytest

from app.services.match_engine import MatchResult, compute_match_score
from app.services.match_engine.formula import _weighted_score
from app.services.match_engine.s_relevance import (
    FULL_RELEVANCE_AT,
    RELEVANCE_FLOOR,
    build_profile_text,
    compute_relevance,
)
from app.tasks.matching import run_match
from tests.fakes import FakeSupabase


def _embedding(seed: float) -> list[float]:
    return [seed, 1.0 - seed, 0.5]


def _profile(index: int) -> dict[str, object]:
    seniorities = ["junior", "mid", "senior", "staff", "principal"]
    modalities = ["remote", "hybrid", "onsite"]
    return {
        "id": f"profile-{index}",
        "user_id": f"user-{index}",
        "target_seniority": seniorities[index % len(seniorities)],
        "work_modality": modalities[index % len(modalities)],
        "target_industry": ["software", "saas"] if index % 2 == 0 else ["finance"],
        "inferred_soft_skills": [],
        "embedding": _embedding(0.8 if index % 2 == 0 else 0.2),
    }


def _job(index: int) -> dict[str, object]:
    seniorities = ["junior", "mid", "senior", "staff", "principal"]
    modalities = ["remote", "hybrid", "onsite"]
    tech_stack = ["python", "fastapi"] if index % 2 == 0 else ["java", "spring"]
    return {
        "id": f"job-{index}",
        "user_id": f"user-{index}",
        "job_title": "Backend Engineer",
        "required_seniority": seniorities[index % len(seniorities)],
        "required_modality": modalities[index % len(modalities)],
        "industry": "software" if index % 2 == 0 else "finance",
        "tech_stack": tech_stack,
        "required_skills": tech_stack,
        "soft_skills": ["problem_solving", "communication"],
        "required_education": "bachelor",
        "required_languages": [{"name": "english", "level": "advanced"}],
        "embedding": _embedding(0.8 if index % 2 == 0 else 0.2),
    }


def _seed_golden_dataset(db: FakeSupabase) -> None:
    db.tables["users"] = [
        {
            "id": f"user-{index}",
            "supabase_uid": f"auth-user-{index}",
            "email": f"user{index}@example.com",
            "tier": "free",
        }
        for index in range(10)
    ]
    db.tables["master_profiles"] = [_profile(index) for index in range(10)]
    db.tables["job_descriptions"] = [_job(index) for index in range(10)]

    for index in range(10):
        profile_id = f"profile-{index}"
        uses_python = index % 2 == 0
        primary_skills = ["python", "fastapi"] if uses_python else ["java", "spring"]
        for skill in primary_skills + ["communication"]:
            db.tables["skills"].append(
                {
                    "id": f"skill-{index}-{skill}",
                    "profile_id": profile_id,
                    "name": skill,
                    "category": "technical" if skill != "communication" else "soft",
                    "level": "advanced",
                    "in_cv": True,
                    "confirmed": True,
                    "embedding": _embedding(0.8 if uses_python else 0.2),
                }
            )
        db.tables["educations"].append(
            {
                "id": f"edu-{index}",
                "profile_id": profile_id,
                "institution": "Tech University",
                "field_of_study": "Computer Science",
                "degree_level": "bachelor",
                "is_ongoing": index % 3 == 0,
                "embedding": _embedding(0.8 if uses_python else 0.2),
            }
        )
        db.tables["certifications"].append(
            {
                "id": f"cert-{index}",
                "profile_id": profile_id,
                "name": "Cloud Practitioner",
            }
        )
        db.tables["languages"].append(
            {
                "id": f"lang-{index}",
                "profile_id": profile_id,
                "name": "english",
                "proficiency": "advanced" if index != 3 else "basic",
            }
        )
        db.tables["experiences"].append(
            {
                "id": f"exp-{index}",
                "profile_id": profile_id,
                "company": "Acme",
                "title": "Engineer",
                "description": "Solved incidents and documented platform decisions.",
                "achievements": ["Improved latency by 20%", "Presented results"],
            }
        )
        db.tables["uploaded_documents"].append(
            {
                "id": f"doc-{index}",
                "user_id": f"user-{index}",
                "profile_id": profile_id,
                "type": "cv",
                "is_primary": True,
                "parsed_data": {
                    "skills": [{"name": skill} for skill in primary_skills]
                },
            }
        )


class FakeReasoningGateway:
    async def generate(
        self,
        _task_type: str,
        _user_tier: str,
        _prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        return (
            "- Buen fit por skills backend.\n"
            "- Agregá React al CV.\n"
            "- Mencioná liderazgo en incidentes."
        )


@pytest.mark.asyncio
async def test_golden_dataset_scores_10_profiles_by_10_jobs() -> None:
    db = FakeSupabase()
    _seed_golden_dataset(db)

    results = []
    for profile_index in range(10):
        for job_index in range(10):
            result = await compute_match_score(
                f"profile-{profile_index}",
                f"job-{job_index}",
                db,
            )
            results.append(result)
            assert 0 <= result.match_score <= 100
            assert result.potential_score >= result.match_score
            assert 0 <= result.representation_score <= 100
            assert result.gap_origin in {"skills", "seniority", "both", "none"}
            assert set(result.score_breakdown["sub_scores"]) == {
                "skills",
                "seniority",
                "education",
                "languages",
                "company",
                "soft",
            }

    same_profile_job = await compute_match_score("profile-0", "job-0", db)
    mismatched_job = await compute_match_score("profile-0", "job-1", db)

    assert same_profile_job.match_score > mismatched_job.match_score
    assert same_profile_job.representation_score == 100
    assert db.tables["master_profiles"][0]["inferred_soft_skills"]
    assert len(results) == 100


@pytest.mark.asyncio
async def test_run_match_persists_full_score_breakdown() -> None:
    db = FakeSupabase()
    _seed_golden_dataset(db)

    match = await run_match(
        "job-0",
        "profile-0",
        "user-0",
        supabase=db,
        gateway=FakeReasoningGateway(),  # type: ignore[arg-type]
    )

    assert match["match_score"] >= 80
    assert match["potential_score"] >= match["match_score"]
    assert match["ai_model_used"] == "deepseek-chat"
    assert match["recommendations"]
    assert db.tables["job_matches"][0]["score_breakdown"]["sub_scores"]["skills"] == 1.0


# --- relevancia del área: un CV de sistemas no sirve para un puesto de chef --------

SYSTEMS_VECTOR = [0.0, 0.0, 1.0]
COOKING_VECTOR = [0.0, 1.0, 0.0]


def _systems_candidate(db: FakeSupabase) -> None:
    """Perfil senior de sistemas: sin ningún componente genérico en contra."""
    db.tables["master_profiles"] = [
        {
            "id": "p1",
            "user_id": "u1",
            "target_seniority": "senior",
            "work_modality": "onsite",
            "target_industry": [],
            "inferred_soft_skills": [],
        }
    ]
    db.tables["skills"] = [
        {
            "id": f"s{index}",
            "profile_id": "p1",
            "name": name,
            "category": "technical",
            "confirmed": True,
            "in_cv": True,
            "embedding": None,
        }
        for index, name in enumerate(["python", "sql", "docker", "aws", "linux"])
    ]
    db.tables["educations"] = [
        {
            "id": "e1",
            "profile_id": "p1",
            "field_of_study": "Ingenieria en Sistemas",
            "degree_level": "bachelor",
        }
    ]
    db.tables["languages"] = [
        {"id": "l1", "profile_id": "p1", "name": "english", "proficiency": "advanced"}
    ]


def _posting(job_id: str, **overrides: object) -> dict[str, object]:
    return {
        "id": job_id,
        "user_id": "u1",
        "job_title": "Chef ejecutivo",
        "raw_text": None,
        "required_seniority": "senior",
        "required_modality": "onsite",
        "industry": "gastronomia",
        "tech_stack": [],
        "required_skills": ["cocina", "haccp", "gestion de inventario", "personal"],
        "soft_skills": [],
        "required_education": None,
        "required_languages": [],
        "embedding": COOKING_VECTOR,
        **overrides,
    }


async def _score(job: dict[str, object]) -> MatchResult:
    db = FakeSupabase()
    _systems_candidate(db)
    db.tables["job_descriptions"] = [job]
    return await compute_match_score("p1", str(job["id"]), db)


@pytest.mark.asyncio
async def test_a_systems_cv_scores_low_for_a_chef_job() -> None:
    result = await _score(_posting("chef"))

    assert result.match_score <= 15
    assert result.score_breakdown["relevance"]["source"] == "skills"
    assert result.score_breakdown["relevance"]["score"] == RELEVANCE_FLOOR


@pytest.mark.asyncio
async def test_a_chef_job_with_no_extracted_skills_still_scores_low() -> None:
    """Sin skills, el motor daba 0,8 por defecto y el puesto sumaba ~80 puntos."""
    result = await _score(
        _posting(
            "chef-sin-skills",
            required_skills=[],
            raw_text="Buscamos chef ejecutivo para la cocina de un restaurante.",
        )
    )

    assert result.match_score <= 15
    assert result.score_breakdown["relevance"]["source"] == "text"


@pytest.mark.asyncio
async def test_a_job_without_skills_that_names_the_candidates_skills_is_relevant() -> (
    None
):
    result = await _score(
        _posting(
            "backend-sin-skills",
            job_title="Backend Engineer",
            industry="software",
            required_skills=[],
            raw_text="Python, SQL, Docker y AWS en un equipo de plataforma.",
        )
    )

    assert result.score_breakdown["relevance"]["score"] == 1.0
    assert result.match_score >= 70


@pytest.mark.asyncio
async def test_a_job_with_no_skills_and_no_text_is_not_penalized() -> None:
    result = await _score(
        _posting("vacio", job_title=None, required_skills=[], raw_text=None)
    )

    assert result.score_breakdown["relevance"] == {
        "score": 1.0,
        "evidence": None,
        "source": "none",
    }


@pytest.mark.asyncio
async def test_a_matching_job_keeps_its_score() -> None:
    result = await _score(
        _posting(
            "backend",
            job_title="Backend Engineer",
            industry="software",
            required_skills=["python", "sql", "docker", "aws"],
        )
    )

    assert result.score_breakdown["relevance"]["score"] == 1.0
    assert result.match_score >= 85


@pytest.mark.asyncio
async def test_the_score_grows_with_the_share_of_required_skills_covered() -> None:
    candidate_skills = ["python", "sql", "docker", "aws", "linux"]
    scores = []
    for covered in (0, 1, 2, 3, 4):
        required = candidate_skills[:covered] + [
            f"otra-{n}" for n in range(8 - covered)
        ]
        result = await _score(
            _posting(f"job-{covered}", job_title="Backend", required_skills=required)
        )
        scores.append(result.match_score)

    assert scores == sorted(scores)
    assert scores[0] <= 15
    # La mitad de lo pedido ya es del área: el gradiente se frena en lo que da el motor.
    assert scores[-1] >= 60


def test_relevance_is_at_the_floor_with_no_overlap_and_full_at_the_threshold() -> None:
    job = {"required_skills": ["a", "b"], "job_title": "x"}

    nothing = compute_relevance([], job, {"score": 0.0})
    enough = compute_relevance([], job, {"score": FULL_RELEVANCE_AT})
    half = compute_relevance([], job, {"score": FULL_RELEVANCE_AT / 2})

    assert nothing["score"] == RELEVANCE_FLOOR
    assert enough["score"] == 1.0
    assert RELEVANCE_FLOOR < half["score"] < 1.0


def test_a_skill_name_inside_another_word_is_not_a_mention() -> None:
    job = {"required_skills": [], "raw_text": "Administración de bases MySQL."}

    result = compute_relevance([{"name": "SQL"}], job, {"score": 0.8})

    assert result["source"] == "text"
    assert result["evidence"] == 0.0


@pytest.mark.asyncio
async def test_the_potential_is_not_reduced_by_the_area() -> None:
    result = await _score(_posting("chef"))

    assert result.potential_score > result.match_score
    assert result.potential_score >= 80


# --- la persona nombra sus skills aunque tenga pocas filas cargadas -------------


def _developer_with_few_skill_rows(db: FakeSupabase) -> None:
    """Una sola fila en `skills`, pero el headline y la bio nombran el resto."""
    _systems_candidate(db)
    db.tables["master_profiles"][0].update(
        {
            "headline": "Full Stack Developer | Python | React",
            "summary": (
                "Mis tecnologías: Python, JavaScript, React, SQL, API REST y Git. "
                "Automatizo flujos de trabajo e integro sistemas."
            ),
        }
    )
    db.tables["skills"] = db.tables["skills"][:1]


async def _score_developer(job: dict[str, object]) -> MatchResult:
    db = FakeSupabase()
    _developer_with_few_skill_rows(db)
    db.tables["job_descriptions"] = [job]
    return await compute_match_score("p1", str(job["id"]), db)


@pytest.mark.asyncio
async def test_a_job_of_the_persons_own_area_is_not_halved_by_few_skill_rows() -> None:
    """En producción un puesto de su rubro daba 21: solo 1 de 6 skills era una fila."""
    result = await _score_developer(
        _posting(
            "fullstack",
            job_title="Desarrollador Full Stack Jr",
            industry="software",
            required_skills=[
                "python",
                "javascript",
                "react",
                "sql",
                "api rest",
                "git",
            ],
        )
    )

    relevance = result.score_breakdown["relevance"]
    assert relevance["source"] == "profile_text"
    assert relevance["score"] == 1.0
    # Sigue siendo bajo en habilidades (1 de 6 filas), pero no se castiga por área.
    assert result.score_breakdown["sub_scores"]["skills"] < 0.2
    assert result.match_score >= 50


@pytest.mark.asyncio
async def test_naming_skills_in_the_bio_does_not_lift_a_job_of_another_area() -> None:
    result = await _score_developer(_posting("chef"))

    assert result.score_breakdown["relevance"]["score"] == RELEVANCE_FLOOR
    assert result.match_score <= 15


def test_the_profile_text_gathers_what_the_person_says_about_themselves() -> None:
    text = build_profile_text(
        {
            "headline": "Chef Ejecutivo",
            "target_role": "Jefe de Cocina",
            "summary": "Lidero equipos",
        },
        [{"name": "HACCP"}, {"name": None}],
        [
            {
                "title": "Sous Chef",
                "description": "Costeo de platos",
                "achievements": ["Redujo mermas un 12%"],
            }
        ],
    )

    for expected in ("chef ejecutivo", "jefe de cocina", "lidero equipos", "haccp"):
        assert expected in text
    assert "sous chef" in text
    assert "costeo de platos" in text
    assert "redujo mermas" in text
    assert "none" not in text


def test_a_required_skill_is_found_in_the_profile_text_ignoring_accents() -> None:
    job = {"required_skills": ["gestión de inventario"]}
    profile_text = build_profile_text(
        {"summary": "Gestion de inventario y costos en cocinas de alto volumen"}, [], []
    )

    result = compute_relevance([], job, {"score": 0.0}, profile_text)

    assert result["source"] == "profile_text"
    assert result["score"] == 1.0


def test_one_letter_skill_names_are_not_searched_in_the_profile_text() -> None:
    job = {"required_skills": ["r"]}

    result = compute_relevance([], job, {"score": 0.0}, "r studio y python")

    assert result["evidence"] == 0.0
    assert result["score"] == RELEVANCE_FLOOR


COMPONENTS = ("skills", "seniority", "education", "languages", "company", "soft")


@pytest.mark.parametrize(
    ("component", "points"),
    [
        ("skills", 35),
        ("seniority", 25),
        ("company", 15),
        ("education", 10),
        ("languages", 10),
        ("soft", 5),
    ],
)
def test_each_component_weighs_what_the_formula_says(
    component: str, points: int
) -> None:
    """Con un solo componente al máximo, el puntaje es exactamente su peso."""
    scores = {name: 1.0 if name == component else 0.0 for name in COMPONENTS}

    assert _weighted_score(scores) == points


def test_the_weights_add_up_to_one_hundred() -> None:
    assert _weighted_score(dict.fromkeys(COMPONENTS, 1.0)) == 100
