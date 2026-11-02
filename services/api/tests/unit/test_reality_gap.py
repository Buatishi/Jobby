"""Reality Gap: qué dice cada documento y en qué difieren.

Antes leía dos marcas (`in_cv`, `in_linkedin`) de las skills confirmadas, y esas marcas
solo se ponían en verdadero. Una cuenta con 59 filas guardadas (39 nombres distintos, 4
confirmadas) mostraba 4; una skill sacada del CV seguía con el visto bueno del CV; y lo
que solo nombraba LinkedIn no se veía. Ahora se compara lo que dice el CV con lo que
dice el PDF de LinkedIn, skill por skill.
"""

from typing import Any

import pytest

from app.services.reality_gap import build_reality_gap, pick_documents


def _saved(
    name: str | None,
    category: str | None = "technical",
    *,
    confirmed: bool = False,
    in_cv: bool = False,
    skill_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": skill_id or f"id-{name}-{category}",
        "name": name,
        "category": category,
        "in_cv": in_cv,
        "in_linkedin": False,
        "confirmed": confirmed,
    }


def _cv(
    *names: str,
    text: str = "",
    status: str = "done",
    legacy: bool = False,
) -> dict[str, Any]:
    """Un CV leído; `extracted_skills` es lo que nombró (los viejos no lo tienen)."""
    parsed: dict[str, Any] = {
        "skills": [{"name": "Cobol", "in_cv": True}],  # la suma de todas las guardadas
        "experiences": [{"title": "", "description": text, "achievements": []}],
    }
    if not legacy:
        parsed["extracted_skills"] = [{"name": n, "category": "x"} for n in names]
    return {
        "type": "cv",
        "status": status,
        "is_primary": True,
        "original_filename": "cv.pdf",
        "created_at": "2026-11-02T14:55:20+00:00",
        "parsed_data": parsed,
    }


def _linkedin(*names: str, text: str = "", status: str = "done") -> dict[str, Any]:
    return {
        "type": "linkedin",
        "status": status,
        "is_primary": False,
        "original_filename": "Profile.pdf",
        "created_at": "2026-10-31T22:50:32+00:00",
        "parsed_data": {
            "skills": [{"name": n, "category": "x"} for n in names],
            "experiences": [{"title": "", "description": text, "achievements": []}],
        },
    }


def _build(
    saved: list[dict[str, Any]],
    *,
    rejected: list[dict[str, Any]] | None = None,
    cv: dict[str, Any] | None = None,
    linkedin: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_reality_gap(saved, rejected or [], cv, linkedin)


def _by_name(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in result["skills"]}


# --- una fila por skill, con el nombre y la categoría de la que la confirmó ---------


def test_the_same_skill_saved_with_several_categories_shows_once() -> None:
    result = _build(
        [
            _saved("Python", "programming language"),
            _saved("Python", "backend"),
            _saved("Python", "programming"),
        ],
        cv=_cv("Python"),
        linkedin=_linkedin("Python"),
    )

    assert len(result["skills"]) == 1
    skill = result["skills"][0]
    assert skill["in_cv"] is True
    assert skill["in_linkedin"] is True
    assert skill["coherence_score"] == 100
    assert skill["recommendation"] is None


def test_names_that_are_the_same_skill_are_grouped() -> None:
    result = _build(
        [_saved("Power BI", "tools"), _saved("Microsoft Power BI", "analytics")],
        cv=_cv("Power BI"),
        linkedin=_linkedin("Microsoft Power BI"),
    )

    assert [item["name"] for item in result["skills"]] == ["Power BI"]
    assert result["skills"][0]["in_cv"] is True
    assert result["skills"][0]["in_linkedin"] is True


def test_a_different_skill_is_not_taken_for_another() -> None:
    result = _build(
        [_saved("Java"), _saved("JavaScript"), _saved("SQL"), _saved("PostgreSQL")],
        cv=_cv("Java", "JavaScript", "SQL", "PostgreSQL"),
        linkedin=_linkedin("JavaScript", "PostgreSQL"),
    )

    skills = _by_name(result)
    assert sorted(skills) == ["Java", "JavaScript", "PostgreSQL", "SQL"]
    assert skills["Java"]["in_linkedin"] is False
    assert skills["SQL"]["in_linkedin"] is False
    assert skills["JavaScript"]["in_linkedin"] is True
    assert skills["PostgreSQL"]["in_linkedin"] is True


def test_unconfirmed_skills_are_included_and_say_so() -> None:
    result = _build(
        [_saved("FastAPI", confirmed=True), _saved("Docker", confirmed=False)],
        cv=_cv("FastAPI", "Docker"),
        linkedin=_linkedin(),
    )

    skills = _by_name(result)
    assert skills["FastAPI"]["confirmed"] is True
    assert skills["Docker"]["confirmed"] is False
    assert skills["Docker"]["saved"] is True
    assert skills["Docker"]["recommendation"] == "Agregá Docker a LinkedIn."


def test_the_confirmed_row_gives_the_group_its_name_category_and_id() -> None:
    result = _build(
        [
            _saved("Python", "backend", skill_id="unconfirmed"),
            _saved("Python", "technical", confirmed=True, skill_id="confirmed"),
        ],
        cv=_cv("Python"),
        linkedin=_linkedin("Python"),
    )

    assert len(result["skills"]) == 1
    skill = result["skills"][0]
    assert skill["skill_id"] == "confirmed"
    assert skill["category"] == "technical"
    assert skill["confirmed"] is True


def test_a_group_without_a_confirmed_row_uses_the_shortest_name() -> None:
    result = _build(
        [_saved("Microsoft Power BI"), _saved("Power BI")],
        cv=_cv("Power BI"),
        linkedin=_linkedin(),
    )

    assert [item["name"] for item in result["skills"]] == ["Power BI"]


def test_skills_without_a_usable_name_are_skipped() -> None:
    result = _build(
        [_saved(None), _saved("   "), {"id": "c", "in_cv": True}],
        cv=_cv("", "   "),
        linkedin=_linkedin(),
    )

    assert result["skills"] == []


# --- rechazadas -----------------------------------------------------------------


def test_a_rejected_skill_that_is_now_confirmed_is_not_rejected() -> None:
    # Python se rechazó en una revisión vieja del asistente y después se confirmó:
    # antes salía «rechazada» con 20 puntos menos y un consejo contradictorio.
    result = _build(
        [_saved("Python", confirmed=True)],
        rejected=[{"name": "Python"}],
        cv=_cv("Python"),
        linkedin=_linkedin("Python"),
    )

    skill = result["skills"][0]
    assert skill["rejected"] is False
    assert skill["coherence_score"] == 100
    assert skill["recommendation"] is None


def test_a_rejected_skill_that_is_still_unconfirmed_stays_rejected() -> None:
    result = _build(
        [_saved("Zapier")],
        rejected=[{"name": "Zapier"}],
        cv=_cv("Zapier"),
        linkedin=_linkedin("Zapier"),
    )

    skill = result["skills"][0]
    assert skill["rejected"] is True
    assert skill["coherence_score"] == 80
    assert skill["recommendation"] == (
        "Revisá si Zapier debe volver al perfil o quedar rechazada."
    )


def test_rejected_names_are_compared_by_their_common_form() -> None:
    result = _build(
        [_saved("React")],
        rejected=[{"name": "React.js"}],
        cv=_cv("React"),
        linkedin=_linkedin(),
    )

    assert result["skills"][0]["rejected"] is True


def test_a_confirmed_row_anywhere_in_the_group_clears_the_rejection() -> None:
    result = _build(
        [
            _saved("Python", "backend", confirmed=False),
            _saved("Python", "technical", confirmed=True),
        ],
        rejected=[{"name": "python"}],
        cv=_cv("Python"),
        linkedin=_linkedin("Python"),
    )

    assert len(result["skills"]) == 1
    assert result["skills"][0]["rejected"] is False


# --- el orden -------------------------------------------------------------------


def test_the_lowest_coherence_comes_first_and_ties_are_alphabetical() -> None:
    result = _build(
        [_saved("Zig"), _saved("Python"), _saved("Ada"), _saved("Rust")],
        cv=_cv("Python", "Rust"),
        linkedin=_linkedin("Python"),
    )

    assert [(i["name"], i["coherence_score"]) for i in result["skills"]] == [
        ("Ada", 20),
        ("Zig", 20),
        ("Rust", 60),
        ("Python", 100),
    ]


# --- lo que dice cada documento --------------------------------------------------


def test_a_skill_taken_out_of_the_cv_stops_counting_as_in_the_cv() -> None:
    # La marca guardada de Python quedó en verdadero con un CV anterior; el CV de hoy
    # ya no la nombra. Antes la marca nunca se apagaba.
    result = _build(
        [_saved("Python", in_cv=True), _saved("Docker", in_cv=True)],
        cv=_cv("Docker"),
        linkedin=_linkedin("Python", "Docker"),
    )

    skills = _by_name(result)
    assert skills["Python"]["in_cv"] is False
    assert (
        skills["Python"]["recommendation"]
        == "Agregá Python al CV para alinear tus canales."
    )
    assert skills["Docker"]["in_cv"] is True


def test_a_skill_taken_out_of_linkedin_stops_counting_as_in_linkedin() -> None:
    result = _build(
        [_saved("Python"), _saved("SQL")],
        cv=_cv("Python", "SQL"),
        linkedin=_linkedin("SQL"),
    )

    assert _by_name(result)["Python"]["in_linkedin"] is False


def test_a_skill_that_only_linkedin_names_shows_up_without_being_saved() -> None:
    result = _build(
        [_saved("Python")],
        cv=_cv("Python"),
        linkedin=_linkedin("Python", "Gestión de Software"),
    )

    skill = _by_name(result)["Gestión de Software"]
    assert skill["saved"] is False
    assert skill["skill_id"] is None
    assert skill["confirmed"] is False
    assert skill["in_cv"] is False
    assert skill["in_linkedin"] is True
    assert skill["category"] == "x"
    assert skill["coherence_score"] == 60
    assert skill["recommendation"] == (
        "Agregá Gestión de Software al CV para alinear tus canales."
    )


def test_a_skill_that_only_the_cv_names_shows_up_without_being_saved() -> None:
    result = _build([], cv=_cv("Terraform"), linkedin=_linkedin())

    skill = _by_name(result)["Terraform"]
    assert skill["saved"] is False
    assert skill["in_cv"] is True
    assert skill["in_linkedin"] is False


def test_an_unsaved_skill_named_by_both_documents_shows_once() -> None:
    result = _build(
        [],
        cv=_cv("React"),
        linkedin=_linkedin("React.js"),
    )

    assert [item["name"] for item in result["skills"]] == ["React"]
    assert result["skills"][0]["in_cv"] is True
    assert result["skills"][0]["in_linkedin"] is True


def test_a_rejected_skill_that_only_linkedin_names_is_still_rejected() -> None:
    result = _build(
        [],
        rejected=[{"name": "Zapier"}],
        cv=_cv(),
        linkedin=_linkedin("Zapier"),
    )

    skill = _by_name(result)["Zapier"]
    assert skill["saved"] is False
    assert skill["rejected"] is True


# --- lo que cuenta el texto del documento ----------------------------------------


def test_a_skill_mentioned_in_the_cv_experience_counts_as_in_the_cv() -> None:
    result = _build(
        [_saved("Docker"), _saved("Python")],
        cv=_cv("Python", text="Desplegué los servicios con Docker y Compose."),
        linkedin=_linkedin(),
    )

    assert _by_name(result)["Docker"]["in_cv"] is True


def test_a_skill_mentioned_in_the_linkedin_experience_counts_as_in_linkedin() -> None:
    result = _build(
        [_saved("Terraform")],
        cv=_cv("Terraform"),
        linkedin=_linkedin(text="Infraestructura como código con Terraform."),
    )

    assert _by_name(result)["Terraform"]["in_linkedin"] is True


@pytest.mark.parametrize(
    ("skill", "text"),
    [
        ("Git", "Marketing digital para pymes."),
        ("SQL", "Administré bases PostgreSQL."),
        ("C", "Programé módulos en C++."),
        ("Java", "Frontend en JavaScript."),
    ],
)
def test_a_name_inside_another_word_is_not_a_mention(skill: str, text: str) -> None:
    result = _build(
        [_saved(skill)],
        cv=_cv(text=text),
        linkedin=_linkedin(),
    )

    assert _by_name(result)[skill]["in_cv"] is False


def test_a_skill_saved_under_a_longer_name_is_found_by_its_common_word() -> None:
    # «Microsoft Excel» y «Excel» son la misma skill: el texto dice «Excel».
    result = _build(
        [_saved("Microsoft Excel"), _saved("ReactJS")],
        cv=_cv(text="Cargué los datos desde Excel y armé la interfaz en React."),
        linkedin=_linkedin(),
    )

    skills = _by_name(result)
    assert skills["Microsoft Excel"]["in_cv"] is True
    assert skills["ReactJS"]["in_cv"] is True


def test_a_common_form_of_several_words_is_not_searched_in_the_text() -> None:
    # «API REST» tiene la forma común «api rest»: sus palabras sueltas no alcanzan.
    result = _build(
        [_saved("API REST")],
        cv=_cv(text="Consumí una api de pagos y un servicio rest de stock."),
        linkedin=_linkedin(),
    )

    assert _by_name(result)["API REST"]["in_cv"] is False


def test_a_skill_listed_in_the_cv_without_text_still_counts() -> None:
    result = _build([_saved("Docker")], cv=_cv("Docker"), linkedin=_linkedin())

    assert _by_name(result)["Docker"]["in_cv"] is True


# --- CV leídos antes de que se guardara la lista propia ---------------------------


def test_a_cv_read_before_the_extracted_list_falls_back_to_the_saved_marks() -> None:
    result = _build(
        [_saved("Python", in_cv=True), _saved("Docker", in_cv=False)],
        cv=_cv(legacy=True),
        linkedin=_linkedin(),
    )

    skills = _by_name(result)
    assert skills["Python"]["in_cv"] is True
    assert skills["Docker"]["in_cv"] is False
    assert result["cv"]["skills_source"] == "saved"


def test_a_legacy_cv_still_finds_a_skill_mentioned_in_its_text() -> None:
    result = _build(
        [_saved("Docker", in_cv=False)],
        cv=_cv(legacy=True, text="Contenedores con Docker."),
        linkedin=_linkedin(),
    )

    assert _by_name(result)["Docker"]["in_cv"] is True


def test_a_cv_with_its_own_list_says_so() -> None:
    result = _build([_saved("Python")], cv=_cv("Python"), linkedin=_linkedin())

    assert result["cv"]["skills_source"] == "document"
    assert result["linkedin"]["skills_source"] == "document"


# --- cuando falta un documento ---------------------------------------------------


def test_without_a_linkedin_document_nothing_is_scored() -> None:
    result = _build([_saved("Python"), _saved("Docker")], cv=_cv("Python"))

    assert result["linkedin"] is None
    assert result["summary"]["comparable"] is False
    assert result["summary"]["score"] is None
    for skill in result["skills"]:
        assert skill["in_linkedin"] is None
        assert skill["coherence_score"] is None
        assert skill["recommendation"] is None
    # El CV sí está: lo que dice se sigue viendo.
    assert _by_name(result)["Python"]["in_cv"] is True
    assert _by_name(result)["Docker"]["in_cv"] is False


def test_without_a_cv_nothing_is_scored() -> None:
    result = _build([_saved("Python")], linkedin=_linkedin("Python"))

    assert result["cv"] is None
    assert result["summary"]["comparable"] is False
    skill = result["skills"][0]
    assert skill["in_cv"] is None
    assert skill["in_linkedin"] is True
    assert skill["coherence_score"] is None


def test_without_documents_the_saved_skills_are_listed_alphabetically() -> None:
    result = _build([_saved("Zig"), _saved("Ada")])

    assert [item["name"] for item in result["skills"]] == ["Ada", "Zig"]
    assert result["summary"]["total"] == 2
    assert result["summary"]["comparable"] is False


@pytest.mark.parametrize("status", ["pending", "processing", "failed"])
def test_a_document_that_was_not_read_does_not_count(status: str) -> None:
    result = _build(
        [_saved("Python")],
        cv=_cv("Python", status=status),
        linkedin=_linkedin("Python"),
    )

    assert result["cv"]["status"] == status
    assert result["cv"]["skills_source"] is None
    assert result["summary"]["comparable"] is False
    assert result["skills"][0]["in_cv"] is None


# --- el resumen ------------------------------------------------------------------


def test_the_summary_counts_each_kind_of_difference_and_averages_the_score() -> None:
    result = _build(
        [_saved("Python"), _saved("Docker"), _saved("Kafka"), _saved("Terraform")],
        cv=_cv("Python", "Docker"),
        linkedin=_linkedin("Python", "Kafka"),
    )

    assert result["summary"] == {
        "comparable": True,
        "total": 4,
        "in_both": 1,
        "only_cv": 1,
        "only_linkedin": 1,
        "in_neither": 1,
        # (100 + 60 + 60 + 20) / 4
        "score": 60,
    }


def test_an_empty_comparison_has_no_score() -> None:
    result = _build([], cv=_cv(), linkedin=_linkedin())

    assert result["skills"] == []
    assert result["summary"]["comparable"] is True
    assert result["summary"]["total"] == 0
    assert result["summary"]["score"] is None


def test_each_document_reports_its_file_and_date() -> None:
    result = _build([], cv=_cv(), linkedin=_linkedin())

    assert result["cv"] == {
        "filename": "cv.pdf",
        "uploaded_at": "2026-11-02T14:55:20+00:00",
        "status": "done",
        "skills_source": "document",
    }
    assert result["linkedin"]["filename"] == "Profile.pdf"
    assert result["linkedin"]["uploaded_at"] == "2026-10-31T22:50:32+00:00"


# --- datos guardados con otra forma ------------------------------------------------


@pytest.mark.parametrize(
    "parsed_data",
    [
        None,
        "texto",
        [],
        {},
        {"skills": None, "extracted_skills": None},
        {"skills": "Python", "extracted_skills": "Python"},
        {"skills": {"name": "Python"}, "experiences": "texto"},
        {"skills": [None, 3, {}, {"name": None}, {"name": 7}], "educations": [None]},
        {"experiences": [None, 3, {"description": 7, "achievements": "uno"}]},
    ],
)
def test_a_document_with_another_shape_does_not_break_the_comparison(
    parsed_data: Any,
) -> None:
    cv = {**_cv("Python"), "parsed_data": parsed_data}
    linkedin = {**_linkedin("Python"), "parsed_data": parsed_data}

    result = _build([_saved("Python")], cv=cv, linkedin=linkedin)

    assert [item["name"] for item in result["skills"]] == ["Python"]
    assert result["summary"]["comparable"] is True


def test_plain_strings_in_the_skill_list_count_as_names() -> None:
    cv = _cv()
    cv["parsed_data"]["extracted_skills"] = ["Python", {"name": "SQL"}]

    result = _build([], cv=cv, linkedin=_linkedin())

    assert sorted(item["name"] for item in result["skills"]) == ["Python", "SQL"]


# --- qué documentos se comparan ----------------------------------------------------


def test_the_primary_cv_and_the_newest_linkedin_are_the_ones_compared() -> None:
    newest_linkedin = {**_linkedin("A"), "id": "li-new"}
    older_cv = {**_cv("B"), "id": "cv-old", "is_primary": False}
    primary_cv = {**_cv("C"), "id": "cv-primary"}
    older_linkedin = {**_linkedin("D"), "id": "li-old"}

    cv, linkedin = pick_documents(
        [newest_linkedin, older_cv, primary_cv, older_linkedin]
    )

    assert cv is not None and cv["id"] == "cv-primary"
    assert linkedin is not None and linkedin["id"] == "li-new"


def test_without_a_primary_cv_the_newest_one_is_used() -> None:
    newer = {**_cv("A"), "id": "cv-new", "is_primary": False}
    older = {**_cv("B"), "id": "cv-old", "is_primary": False}

    cv, linkedin = pick_documents([newer, older])

    assert cv is not None and cv["id"] == "cv-new"
    assert linkedin is None


def test_no_documents_means_nothing_to_compare() -> None:
    assert pick_documents([]) == (None, None)
    assert pick_documents([{"type": "other"}]) == (None, None)
