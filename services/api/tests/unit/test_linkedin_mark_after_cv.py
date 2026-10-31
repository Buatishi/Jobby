"""La marca `in_linkedin` no depende del orden en que se suben el PDF y el CV.

El PDF de LinkedIn solo marca las skills que la persona ya tiene al subirlo. Con el CV
subido después, sus skills nacían sin la marca y nada las volvía a marcar: el documento
de LinkedIn contaba la mitad de sus 12 puntos y el perfil se quedaba en 94 %, sin poder
generar el kit de entrevista. Ahora el CV vuelve a aplicar los nombres que el PDF dejó
guardados en su `parsed_data`.
"""

from typing import Any

import pytest

from app.services.cv_parser import (
    PdfContent,
    linkedin_skill_names,
    mark_skills_in_linkedin,
)
from app.services.cv_parser.ai_structurer import CVStructuredData, ParsedSkill
from app.tasks import parsing
from tests.fakes import FakeSupabase

STORED_VECTOR = [0.5] * 4


def _row(skill_id: str, name: str, **overrides: Any) -> dict[str, Any]:
    return {
        "id": skill_id,
        "profile_id": "profile-1",
        "name": name,
        "category": "technical",
        "level": None,
        "in_cv": True,
        "in_linkedin": False,
        "confirmed": False,
        "embedding": STORED_VECTOR,
        **overrides,
    }


# --- los nombres que dejó el PDF -------------------------------------------------


def test_the_names_come_from_the_skills_of_the_saved_document() -> None:
    parsed = {
        "skills": [{"name": "Python", "category": "x"}, {"name": "SQL"}],
        "matched_skills": 2,
    }

    assert linkedin_skill_names(parsed) == ["Python", "SQL"]


@pytest.mark.parametrize(
    "parsed_data",
    [
        None,
        "texto",
        [],
        {},
        {"skills": None},
        {"skills": "Python"},
        {"skills": {"name": "Python"}},
        {"skills": [None, 3, "Python", ["Python"], {}, {"name": None}, {"name": 7}]},
    ],
)
def test_a_saved_document_with_another_shape_names_nothing(parsed_data: Any) -> None:
    assert linkedin_skill_names(parsed_data) == []


def test_malformed_entries_are_dropped_and_the_good_ones_kept() -> None:
    parsed = {"skills": [None, {"name": "Python"}, {"name": 3}, {"name": "Docker"}]}

    assert linkedin_skill_names(parsed) == ["Python", "Docker"]


# --- qué skills se marcan --------------------------------------------------------


def test_the_skills_named_by_the_pdf_are_marked() -> None:
    skills = [_row("s1", "Python"), _row("s2", "SQL"), _row("s3", "Docker")]

    marked = mark_skills_in_linkedin(skills, ["python", "Docker"])

    assert [skill["in_linkedin"] for skill in marked] == [True, False, True]


def test_the_same_alias_and_translation_rules_apply() -> None:
    skills = [
        _row("s1", "React"),
        _row("s2", "Integración de APIs"),
        _row("s3", "React Native"),
        _row("s4", "Java"),
    ]

    marked = mark_skills_in_linkedin(
        skills, ["React.js", "API Integrations", "JavaScript"]
    )

    assert [skill["in_linkedin"] for skill in marked] == [True, True, False, False]


def test_marking_leaves_the_rest_of_each_skill_alone_and_the_input_untouched() -> None:
    skills = [_row("s1", "Python", confirmed=True, in_cv=False)]

    marked = mark_skills_in_linkedin(skills, ["Python"])

    assert marked[0]["confirmed"] is True
    assert marked[0]["in_cv"] is False
    assert marked[0]["embedding"] == STORED_VECTOR
    assert skills[0]["in_linkedin"] is False


def test_without_names_the_skills_come_back_unchanged() -> None:
    skills = [_row("s1", "Python", in_linkedin=True), _row("s2", "SQL")]

    assert mark_skills_in_linkedin(skills, []) == skills
    assert mark_skills_in_linkedin(skills, ["", "  ", 3]) == skills


def test_a_skill_without_a_name_is_never_marked() -> None:
    marked = mark_skills_in_linkedin([{"id": "s1"}, {"name": None}], ["Python"])

    assert marked == [{"id": "s1"}, {"name": None}]


# --- el parseo de un CV cuando el PDF de LinkedIn ya estaba ----------------------


class VectorGateway:
    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 4 for _text in texts]


def _world(linkedin_skills: list[str] | str | None = None) -> FakeSupabase:
    """Un perfil con su PDF de LinkedIn ya leído y el CV recién subido.

    `linkedin_skills` son los nombres que dejó el PDF; un texto simula un `parsed_data`
    con otra forma.
    """
    named: Any = (
        linkedin_skills
        if isinstance(linkedin_skills, str)
        else [{"name": name} for name in linkedin_skills or []]
    )
    supabase = FakeSupabase()
    supabase.storage.files["user-1/cv.pdf"] = b"%PDF-1.4 fake"
    supabase.tables["uploaded_documents"].extend(
        [
            {
                "id": "linkedin-1",
                "user_id": "user-1",
                "profile_id": "profile-1",
                "type": "linkedin",
                "storage_path": "user-1/linkedin.pdf",
                "status": "done",
                "created_at": "2026-10-22T02:55:09+00:00",
                "parsed_data": {"skills": named, "matched_skills": 0},
            },
            {
                "id": "document-1",
                "user_id": "user-1",
                "profile_id": "profile-1",
                "type": "cv",
                "storage_path": "user-1/cv.pdf",
                "status": "pending",
                "created_at": "2026-10-31T22:23:47+00:00",
            },
        ]
    )
    return supabase


def _use_parser(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    async def fake_extract_pdf_content(_path: Any) -> PdfContent:
        return PdfContent("texto del CV", None)

    async def fake_structure_cv_text(_text: str) -> CVStructuredData:
        return CVStructuredData(
            skills=[
                ParsedSkill(name=name, category="other", level="intermediate")
                for name in names
            ]
        )

    monkeypatch.setattr(parsing, "extract_pdf_content", fake_extract_pdf_content)
    monkeypatch.setattr(parsing, "structure_cv_text", fake_structure_cv_text)


async def _parse_cv(supabase: FakeSupabase) -> None:
    await parsing.run_parse_cv(
        "document-1",
        supabase=supabase,
        gateway=VectorGateway(),  # type: ignore[arg-type]
    )


def _by_name(supabase: FakeSupabase) -> dict[str, dict[str, Any]]:
    return {row["name"]: row for row in supabase.tables["skills"]}


@pytest.mark.asyncio
async def test_a_cv_uploaded_after_linkedin_marks_the_skills_the_pdf_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world(["Python", "React.js", "Docker", "Kubernetes"])
    _use_parser(monkeypatch, "Python", "React", "Docker", "Terraform")

    await _parse_cv(supabase)

    skills = _by_name(supabase)
    assert skills["Python"]["in_linkedin"] is True
    assert skills["React"]["in_linkedin"] is True
    assert skills["Docker"]["in_linkedin"] is True
    # Lo que el PDF no nombró no se marca, y lo que solo nombró el PDF no se agrega.
    assert skills["Terraform"]["in_linkedin"] is False
    assert "Kubernetes" not in skills
    assert all(row["in_cv"] is True for row in skills.values())


@pytest.mark.asyncio
async def test_the_linkedin_document_gets_its_twelve_points_whatever_the_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world(["Python", "SQL", "Docker"])
    supabase.tables["master_profiles"][0]["completeness_pct"] = 0
    _use_parser(monkeypatch, "Python", "SQL", "Docker")

    await _parse_cv(supabase)

    # 8 del headline del perfil, 20 del CV y los 12 completos del documento de LinkedIn
    # (con la marca perdida eran 6: el 94 % que no dejaba generar el kit).
    assert supabase.tables["master_profiles"][0]["completeness_pct"] == 8 + 20 + 12


@pytest.mark.asyncio
async def test_a_cv_uploaded_again_marks_the_rows_that_were_already_saved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world(["Python", "SQL", "Docker"])
    # Con la categoría que el lector vuelve a inferir («other»): el CV no agrega copias.
    supabase.tables["skills"].extend(
        [
            _row("s-python", "Python", category="other"),
            _row("s-sql", "SQL", category="other", confirmed=True),
            _row("s-docker", "Docker", category="other"),
            _row("s-go", "Go", category="other"),
        ]
    )
    _use_parser(monkeypatch, "Python", "SQL")

    await _parse_cv(supabase)

    skills = _by_name(supabase)
    assert [skills[name]["in_linkedin"] for name in ("Python", "SQL", "Docker")] == [
        True,
        True,
        True,
    ]
    assert skills["Go"]["in_linkedin"] is False
    assert skills["SQL"]["confirmed"] is True
    # Marcar no duplica filas: las que ya estaban se actualizan por su `id`.
    assert len(supabase.tables["skills"]) == 4


@pytest.mark.asyncio
async def test_every_copy_of_a_skill_the_pdf_named_is_marked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Un CV que infiere otra categoría deja la skill repetida (límite conocido de la
    # Decisión 31): las dos copias tienen que quedar marcadas, no solo una.
    supabase = _world(["Python"])
    supabase.tables["skills"].append(_row("s-python", "Python", category="technical"))
    _use_parser(monkeypatch, "Python")

    await _parse_cv(supabase)

    copies = [row for row in supabase.tables["skills"] if row["name"] == "Python"]
    assert len(copies) == 2
    assert all(row["in_linkedin"] is True for row in copies)


@pytest.mark.asyncio
async def test_a_profile_without_a_linkedin_pdf_is_read_as_before(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world(["Python"])
    supabase.tables["uploaded_documents"][:] = [
        row
        for row in supabase.tables["uploaded_documents"]
        if row["type"] != "linkedin"
    ]
    _use_parser(monkeypatch, "Python", "SQL")

    await _parse_cv(supabase)

    assert all(row["in_linkedin"] is False for row in supabase.tables["skills"])


@pytest.mark.asyncio
async def test_a_linkedin_pdf_that_did_not_finish_is_not_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world(["Python"])
    supabase.tables["uploaded_documents"][0]["status"] = "failed"
    _use_parser(monkeypatch, "Python")

    await _parse_cv(supabase)

    assert _by_name(supabase)["Python"]["in_linkedin"] is False


@pytest.mark.asyncio
async def test_the_pdf_of_another_profile_is_not_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world(["Python"])
    supabase.tables["uploaded_documents"][0]["profile_id"] = "profile-2"
    _use_parser(monkeypatch, "Python")

    await _parse_cv(supabase)

    assert _by_name(supabase)["Python"]["in_linkedin"] is False


@pytest.mark.asyncio
async def test_only_the_newest_linkedin_pdf_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world(["Python"])
    supabase.tables["uploaded_documents"].append(
        {
            "id": "linkedin-2",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": "linkedin",
            "storage_path": "user-1/linkedin-2.pdf",
            "status": "done",
            "created_at": "2026-10-30T10:00:00+00:00",
            "parsed_data": {"skills": [{"name": "SQL"}]},
        }
    )
    _use_parser(monkeypatch, "Python", "SQL")

    await _parse_cv(supabase)

    skills = _by_name(supabase)
    assert skills["SQL"]["in_linkedin"] is True
    assert skills["Python"]["in_linkedin"] is False


@pytest.mark.asyncio
async def test_a_saved_pdf_with_a_broken_shape_does_not_fail_the_cv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world("esto no es una lista")
    _use_parser(monkeypatch, "Python")

    await _parse_cv(supabase)

    assert supabase.tables["uploaded_documents"][1]["status"] == "done"
    assert _by_name(supabase)["Python"]["in_linkedin"] is False


@pytest.mark.asyncio
async def test_a_failure_reading_the_pdf_names_does_not_fail_the_cv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = _world(["Python"])
    _use_parser(monkeypatch, "Python")

    async def exploding(_supabase: Any, _profile_id: str) -> list[str]:
        raise RuntimeError("la base no respondió")

    monkeypatch.setattr(parsing, "_saved_linkedin_skill_names", exploding)

    await _parse_cv(supabase)

    document = supabase.tables["uploaded_documents"][1]
    assert document["status"] == "done"
    assert _by_name(supabase)["Python"]["in_cv"] is True
