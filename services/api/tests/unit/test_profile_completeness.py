"""Porcentaje de perfil completo: reglas de calidad y que quede guardado.

Dos cosas se prueban acá. Que el porcentaje no premie relleno ni datos mal cargados, y
que el número calculado quede en `master_profiles.completeness_pct`: la función SQL
anterior lo devolvía y nadie lo guardaba, así que en producción ningún perfil pasaba de
38 y el umbral de 60 para analizar un puesto era inalcanzable.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import profiles as profiles_api
from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.cv_parser.ai_structurer import (
    CVStructuredData,
    ParsedExperience,
    ParsedSkill,
)
from app.services.profile_completeness import (
    WEIGHTS,
    compute_completeness,
    refresh_completeness,
)
from app.tasks import parsing
from tests.fakes import FakeSupabase

GOOD_SUMMARY = (
    "Desarrollador backend con 5 años de experiencia construyendo APIs en Python "
    "para fintech y sistemas de pagos"
)
LINKEDIN = "https://www.linkedin.com/in/juan-perez"


def _profile(**overrides: Any) -> dict[str, Any]:
    return {
        "headline": None,
        "summary": None,
        "target_role": None,
        "target_seniority": None,
        "work_modality": None,
        "linkedin_url": None,
        **overrides,
    }


def _skills(*names: str, confirmed: bool = True, in_cv: bool = False) -> list[dict]:
    return [{"name": name, "confirmed": confirmed, "in_cv": in_cv} for name in names]


def _points(
    profile: dict[str, Any] | None = None,
    *,
    experiences: list[dict[str, Any]] | None = None,
    skills: list[dict[str, Any]] | None = None,
    educations: list[dict[str, Any]] | None = None,
    languages: list[dict[str, Any]] | None = None,
    documents: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    return compute_completeness(
        profile or _profile(),
        experiences or [],
        skills or [],
        educations or [],
        languages or [],
        documents or [],
    ).points


def _full_profile_inputs() -> dict[str, Any]:
    return {
        "profile": _profile(
            headline="Backend Engineer",
            summary=GOOD_SUMMARY,
            target_role="Staff Engineer",
            target_seniority="senior",
            work_modality="remote",
            linkedin_url=LINKEDIN,
        ),
        "experiences": [{"title": "Backend Engineer", "company": "Acme"}],
        "skills": _skills("Python", "FastAPI", "PostgreSQL", in_cv=True),
        "educations": [{"institution": "UTN", "field_of_study": None}],
        "languages": [{"name": "Inglés"}],
        "documents": [
            {"type": "cv", "status": "done"},
            {"type": "linkedin", "status": "done"},
        ],
    }


# --- la suma ------------------------------------------------------------------


def test_the_weights_add_up_to_one_hundred() -> None:
    assert sum(WEIGHTS.values()) == 100


def test_an_empty_profile_scores_zero() -> None:
    result = compute_completeness(_profile(), [], [], [], [], [])

    assert result.score == 0
    assert set(result.points) == set(WEIGHTS)


def test_a_complete_and_useful_profile_scores_one_hundred() -> None:
    result = compute_completeness(**_full_profile_inputs())

    assert result.score == 100
    assert result.points == WEIGHTS


# --- texto de relleno en el perfil --------------------------------------------


@pytest.mark.parametrize(
    "headline",
    ["asdf", "n/a", "Profesional", "Persona responsable", "aaaa", "...", "test"],
)
def test_a_filler_headline_earns_nothing(headline: str) -> None:
    assert _points(_profile(headline=headline))["headline"] == 0


@pytest.mark.parametrize("headline", ["Chef", "Backend Engineer", "Contador público"])
def test_a_real_headline_earns_its_points(headline: str) -> None:
    assert _points(_profile(headline=headline))["headline"] == WEIGHTS["headline"]


@pytest.mark.parametrize(
    "summary",
    [
        "Soy una persona responsable y proactiva con ganas de aprender",
        "asdf asdf asdf asdf asdf asdf asdf",
        "chef chef chef chef chef chef chef",
        "Ingeniero de software",
        "hola",
        "n/a",
    ],
)
def test_a_bio_without_useful_information_earns_nothing(summary: str) -> None:
    assert _points(_profile(summary=summary))["summary"] == 0


def test_an_informative_bio_earns_its_points() -> None:
    assert _points(_profile(summary=GOOD_SUMMARY))["summary"] == WEIGHTS["summary"]


def test_a_bio_that_copies_the_headline_earns_nothing() -> None:
    long_text = "Ingeniero de software backend especializado en sistemas distribuidos"

    points = _points(_profile(headline=long_text, summary=long_text))

    assert points["headline"] == WEIGHTS["headline"]
    assert points["summary"] == 0


@pytest.mark.parametrize("role", ["asdf", "n/a", "Profesional", "x"])
def test_a_filler_target_role_earns_nothing(role: str) -> None:
    assert _points(_profile(target_role=role))["target_role"] == 0


@pytest.mark.parametrize(
    ("field", "value", "earned"),
    [
        ("target_seniority", "senior", True),
        ("target_seniority", "Mid", True),
        ("target_seniority", "semi senior", False),
        ("target_seniority", "asdf", False),
        ("work_modality", "remote", True),
        ("work_modality", "Hybrid", True),
        ("work_modality", "remoto", False),
        ("work_modality", "cualquiera", False),
    ],
)
def test_seniority_and_modality_must_be_values_the_engine_understands(
    field: str, value: str, earned: bool
) -> None:
    # Cualquier otro valor cae al puntaje neutro del motor: no sirve para comparar.
    points = _points(_profile(**{field: value}))

    assert points[field] == (WEIGHTS[field] if earned else 0)


# --- experiencia, skills, estudios e idiomas -----------------------------------


@pytest.mark.parametrize(
    "row",
    [
        {"title": "asdf", "company": "Acme"},
        {"title": "Chef", "company": "n/a"},
        {"title": "", "company": "Acme"},
        {"title": "Chef", "company": None},
    ],
)
def test_an_experience_without_a_real_role_and_company_earns_nothing(
    row: dict[str, Any],
) -> None:
    assert _points(experiences=[row])["experience"] == 0


def test_an_experience_with_role_and_company_earns_its_points() -> None:
    points = _points(experiences=[{"title": "Chef", "company": "La Cabrera"}])

    assert points["experience"] == WEIGHTS["experience"]


def test_one_useful_experience_is_enough_among_junk() -> None:
    rows = [
        {"title": "asdf", "company": "asdf"},
        {"title": "Chef", "company": "La Cabrera"},
    ]

    assert _points(experiences=rows)["experience"] == WEIGHTS["experience"]


def test_skills_need_three_distinct_confirmed_real_names() -> None:
    assert _points(skills=_skills("Python", "SQL"))["skills"] == 0
    assert _points(skills=_skills("Python", "SQL", "Docker"))["skills"] == 10


def test_repeated_filler_and_unconfirmed_skills_do_not_count() -> None:
    skills = [
        *_skills("Python", "python ", "PYTHON"),
        *_skills("asdf", "n/a", "test"),
        *_skills("SQL", confirmed=False),
    ]

    assert _points(skills=skills)["skills"] == 0


def test_education_accepts_the_institution_or_the_field_of_study() -> None:
    wizard = [{"institution": "UTN", "field_of_study": None}]
    parsed = [{"institution": "", "field_of_study": "Ingeniería en Sistemas"}]
    junk = [{"institution": "asdf", "field_of_study": "n/a"}]

    assert _points(educations=wizard)["education"] == WEIGHTS["education"]
    assert _points(educations=parsed)["education"] == WEIGHTS["education"]
    assert _points(educations=junk)["education"] == 0


@pytest.mark.parametrize(("name", "earned"), [("Inglés", True), ("n/a", False)])
def test_a_language_needs_a_real_name(name: str, earned: bool) -> None:
    points = _points(languages=[{"name": name}])

    assert points["languages"] == (WEIGHTS["languages"] if earned else 0)


# --- el CV y el documento de LinkedIn ------------------------------------------


@pytest.mark.parametrize(
    ("document", "skills", "expected"),
    [
        ({"type": "cv", "status": "pending"}, ["Python", "SQL", "Docker"], 0),
        ({"type": "cv", "status": "failed"}, ["Python", "SQL", "Docker"], 0),
        # Terminó pero no dejó nada: un PDF escaneado o ruido.
        ({"type": "cv", "status": "done"}, [], 0),
        ({"type": "cv", "status": "done"}, ["asdf", "n/a"], 0),
        # Dejó poco.
        ({"type": "cv", "status": "done"}, ["Python"], 10),
        # Dejó lo suficiente para comparar.
        ({"type": "cv", "status": "done"}, ["Python", "SQL", "Docker"], 20),
    ],
)
def test_a_cv_counts_for_what_it_left_in_the_profile(
    document: dict[str, Any], skills: list[str], expected: int
) -> None:
    points = _points(
        skills=_skills(*skills, confirmed=False, in_cv=True), documents=[document]
    )

    assert points["cv"] == expected


def test_skills_added_by_hand_do_not_make_a_cv_useful() -> None:
    # `in_cv` queda en falso para lo que se carga a mano: no sale del documento.
    points = _points(
        skills=_skills("Python", "SQL", "Docker", in_cv=False),
        documents=[{"type": "cv", "status": "done"}],
    )

    assert points["cv"] == 0


def test_a_cv_that_only_left_an_experience_earns_half() -> None:
    points = _points(
        experiences=[{"title": "Chef", "company": "La Cabrera"}],
        documents=[{"type": "cv", "status": "done"}],
    )

    assert points["cv"] == WEIGHTS["cv"] // 2


def test_the_linkedin_document_uses_the_same_rule() -> None:
    document = [{"type": "linkedin", "status": "done"}]

    assert _points(documents=document)["linkedin_document"] == 0
    assert (
        _points(
            skills=_skills("Python", "SQL", "Docker", confirmed=False, in_cv=True),
            documents=document,
        )["linkedin_document"]
        == WEIGHTS["linkedin_document"]
    )


@pytest.mark.parametrize(
    ("url", "earned"),
    [
        (LINKEDIN, True),
        ("linkedin.com/in/juan-perez", True),
        ("https://example.com/in/juan-perez", False),
        ("https://www.linkedin.com/company/acme", False),
        ("asdf", False),
    ],
)
def test_the_linkedin_url_must_be_a_profile(url: str, earned: bool) -> None:
    points = _points(_profile(linkedin_url=url))

    assert points["linkedin_url"] == (WEIGHTS["linkedin_url"] if earned else 0)


# --- que el valor quede guardado ----------------------------------------------


async def _fake_current_user() -> CurrentUser:
    return CurrentUser(
        id="user-1", supabase_uid="auth-user-1", email="person@example.com"
    )


def _use(fake_supabase: FakeSupabase) -> None:
    async def fake_client() -> FakeSupabase:
        return fake_supabase

    app.dependency_overrides[get_current_user] = _fake_current_user
    app.dependency_overrides[get_supabase_client] = fake_client


def _stored(fake_supabase: FakeSupabase) -> int:
    return int(fake_supabase.tables["master_profiles"][0]["completeness_pct"])


@pytest.mark.asyncio
async def test_refresh_computes_from_the_rows_and_stores_the_result() -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["skills"] = [
        {"profile_id": "profile-1", "name": name, "confirmed": True, "in_cv": False}
        for name in ("Python", "SQL", "Docker")
    ]

    score = await refresh_completeness(fake_supabase, "profile-1")

    # headline «Backend Engineer» (8) + tres skills confirmadas (10).
    assert score == 18
    assert _stored(fake_supabase) == 18


@pytest.mark.asyncio
async def test_refresh_does_not_read_the_heavy_columns() -> None:
    """`skills.embedding` y `parsed_data` pesan decenas de KB: solo pide columnas."""
    fake_supabase = FakeSupabase()
    requested: list[tuple[str, str]] = []
    original_table = fake_supabase.table

    def spying_table(table_name: str) -> Any:
        query = original_table(table_name)
        original_select = query.select

        def select(columns: str) -> Any:
            requested.append((table_name, columns))
            return original_select(columns)

        query.select = select  # type: ignore[method-assign]
        return query

    fake_supabase.table = spying_table  # type: ignore[method-assign]

    await refresh_completeness(fake_supabase, "profile-1")

    assert requested
    assert all(columns != "*" for _table, columns in requested)
    assert not any("embedding" in columns for _table, columns in requested)
    assert not any("parsed_data" in columns for _table, columns in requested)


def test_patch_profile_stores_the_percentage(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    _use(fake_supabase)

    response = client.patch(
        "/api/v1/profiles/me",
        json={"summary": GOOD_SUMMARY, "target_seniority": "senior"},
    )

    # headline (8) + bio (8) + seniority (4)
    assert response.status_code == 200
    assert response.json()["completeness_pct"] == 20
    assert _stored(fake_supabase) == 20


def test_patch_profile_with_filler_does_not_raise_the_percentage(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()
    _use(fake_supabase)

    response = client.patch(
        "/api/v1/profiles/me",
        json={"headline": "asdf", "summary": "n/a", "target_role": "test"},
    )

    assert response.status_code == 200
    assert response.json()["completeness_pct"] == 0
    assert _stored(fake_supabase) == 0


@pytest.mark.parametrize(
    ("path", "payload", "expected"),
    [
        ("skills", {"name": "Python", "confirmed": True}, 8),
        (
            "experiences",
            {"company": "La Cabrera", "title": "Chef", "achievements": []},
            20,
        ),
        ("educations", {"institution": "UTN"}, 16),
        ("languages", {"name": "Inglés", "level": "professional"}, 12),
    ],
)
def test_adding_profile_data_stores_the_new_percentage(
    client: TestClient, path: str, payload: dict[str, Any], expected: int
) -> None:
    """Antes el RPC calculaba el número y se descartaba: el guardado seguía en 8."""
    fake_supabase = FakeSupabase()
    fake_supabase.tables["master_profiles"][0]["completeness_pct"] = 8
    _use(fake_supabase)

    response = client.post(f"/api/v1/profiles/{path}", json=payload)

    assert response.status_code == 201
    assert _stored(fake_supabase) == expected


def test_the_third_confirmed_skill_unlocks_the_skills_points(
    client: TestClient,
) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["skills"] = [
        {
            "id": f"skill-{name}",
            "profile_id": "profile-1",
            "name": name,
            "category": "technical",
            "confirmed": True,
            "in_cv": True,
        }
        for name in ("Python", "SQL")
    ]
    _use(fake_supabase)

    response = client.post(
        "/api/v1/profiles/skills",
        json={"name": "Docker", "category": "technical", "confirmed": True},
    )

    assert response.status_code == 201
    assert _stored(fake_supabase) == WEIGHTS["headline"] + WEIGHTS["skills"]


def test_deleting_the_cv_stores_the_lower_percentage(client: TestClient) -> None:
    fake_supabase = FakeSupabase()
    fake_supabase.tables["master_profiles"][0]["completeness_pct"] = 99
    fake_supabase.tables["skills"] = [
        {
            "id": f"skill-{name}",
            "profile_id": "profile-1",
            "name": name,
            "confirmed": False,
            "in_cv": True,
        }
        for name in ("Python", "SQL", "Docker")
    ]
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "document-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": "cv",
            "status": "done",
            "storage_path": "auth-user-1/cv.pdf",
        }
    )
    _use(fake_supabase)

    response = client.delete("/api/v1/profiles/documents/document-1")

    assert response.status_code == 204
    assert _stored(fake_supabase) == WEIGHTS["headline"]


def test_a_failing_recalculation_does_not_fail_the_write(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken(_supabase: Any, _profile_id: str) -> int:
        raise RuntimeError("base no disponible")

    monkeypatch.setattr(profiles_api, "refresh_completeness", broken)
    fake_supabase = FakeSupabase()
    _use(fake_supabase)

    response = client.post(
        "/api/v1/profiles/languages", json={"name": "Inglés", "level": "advanced"}
    )

    assert response.status_code == 201
    assert fake_supabase.tables["languages"][0]["name"] == "Inglés"


class _FakeGateway:
    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _text in texts]


def _fake_with_cv() -> FakeSupabase:
    fake_supabase = FakeSupabase()
    fake_supabase.storage.files["user-1/cv.pdf"] = b"%PDF-1.4 fake"
    fake_supabase.tables["uploaded_documents"].append(
        {
            "id": "document-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": "cv",
            "storage_path": "user-1/cv.pdf",
            "status": "pending",
        }
    )
    return fake_supabase


def _patch_parser(
    monkeypatch: pytest.MonkeyPatch, structured: CVStructuredData
) -> None:
    async def fake_extract_pdf_text(_path: Any) -> str:
        return "texto del CV"

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return structured

    monkeypatch.setattr(parsing, "extract_pdf_text", fake_extract_pdf_text)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)


@pytest.mark.asyncio
async def test_parsing_a_useful_cv_stores_the_percentage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = _fake_with_cv()
    _patch_parser(
        monkeypatch,
        CVStructuredData(
            skills=[
                ParsedSkill(name="Python", category="technical"),
                ParsedSkill(name="SQL", category="technical"),
                ParsedSkill(name="Docker", category="technical"),
            ],
            experiences=[ParsedExperience(company="Acme", title="Backend Engineer")],
        ),
    )

    await parsing.run_parse_cv(
        "document-1",
        supabase=fake_supabase,
        gateway=_FakeGateway(),  # type: ignore[arg-type]
    )

    # headline (8) + CV con tres skills leídas (20)
    assert fake_supabase.tables["uploaded_documents"][0]["status"] == "done"
    assert _stored(fake_supabase) == WEIGHTS["headline"] + WEIGHTS["cv"]


@pytest.mark.asyncio
async def test_parsing_a_cv_that_left_only_noise_does_not_earn_the_cv_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_supabase = _fake_with_cv()
    _patch_parser(
        monkeypatch,
        CVStructuredData(skills=[ParsedSkill(name="asdf"), ParsedSkill(name="n/a")]),
    )

    await parsing.run_parse_cv(
        "document-1",
        supabase=fake_supabase,
        gateway=_FakeGateway(),  # type: ignore[arg-type]
    )

    assert fake_supabase.tables["uploaded_documents"][0]["status"] == "done"
    assert _stored(fake_supabase) == WEIGHTS["headline"]


@pytest.mark.asyncio
async def test_a_failing_recalculation_does_not_mark_the_cv_as_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def broken(_supabase: Any, _profile_id: str) -> int:
        raise RuntimeError("base no disponible")

    fake_supabase = _fake_with_cv()
    _patch_parser(monkeypatch, CVStructuredData(skills=[ParsedSkill(name="Python")]))
    monkeypatch.setattr(parsing, "refresh_completeness", broken)

    result = await parsing.run_parse_cv(
        "document-1",
        supabase=fake_supabase,
        gateway=_FakeGateway(),  # type: ignore[arg-type]
    )

    assert result["skills"]
    assert fake_supabase.tables["uploaded_documents"][0]["status"] == "done"
