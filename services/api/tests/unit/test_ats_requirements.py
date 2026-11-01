"""Los requisitos del puesto contra lo que muestra la persona (Decisión 42).

Reglas del autor (2026-10-31): los años salen solo de puestos de trabajo (freelance,
por cuenta propia, pyme o empresa grande) y solo cuenta la experiencia directa con lo
que pide el puesto; y superar lo pedido cuenta como cumplido, con una nota que no resta
puntos.
"""

from datetime import date
from typing import Any

import pytest

from app.models.ats import ATSKeywordMatch, ATSRequirement
from app.services.ats_analyzer.experience import (
    assess_roles,
    describe_months,
    direct_months,
    required_years,
)
from app.services.ats_analyzer.requirements import (
    education_rank,
    evaluate_requirements,
)
from app.services.ats_analyzer.scoring import compose_ats_score, keyword_coverage

TODAY = date(2026, 10, 31)
JOB: dict[str, Any] = {
    "job_title": "Sr Python Developer",
    "required_seniority": "Senior",
    "tech_stack": ["Python"],
    "required_skills": ["Python", "Software design"],
    "raw_text": "Our history spans over 200 years. We build banking software.",
}


def _role(
    title: str,
    started: str | None,
    ended: str | None,
    *,
    company: str = "",
    description: str = "",
    current: bool = False,
) -> dict[str, Any]:
    return {
        "title": title,
        "company": company,
        "started_at": started,
        "ended_at": ended,
        "is_current": current,
        "description": description,
        "achievements": [],
    }


# --- meses y puestos ------------------------------------------------------------


def test_months_are_counted_whole_march_to_may_is_three() -> None:
    roles = assess_roles([_role("Python Developer", "2026-03", "2026-05")], JOB, TODAY)

    assert direct_months(roles) == 3


def test_two_roles_at_the_same_time_count_once() -> None:
    roles = assess_roles(
        [
            _role("Python Developer", "2026-01", "2026-06"),
            _role("Backend Developer", "2026-04", "2026-09", description="Python"),
        ],
        JOB,
        TODAY,
    )

    # Enero a septiembre: nueve meses, no once.
    assert direct_months(roles) == 9


def test_the_authors_case_six_direct_months_beside_unrelated_work() -> None:
    roles = assess_roles(
        [
            _role("Desarrollador Freelance — Python & Salesforce", "2026-01", "2026-03",
                  company="Pyme"),
            _role("Desarrollador Python", "2026-07", "2026-09", company="Paogi"),
            _role("Operador y Analista Digital", "2024-01", "2024-10",
                  company="Independiente", description="Venta de productos online"),
        ],
        JOB,
        TODAY,
    )  # fmt: skip

    assert direct_months(roles) == 6
    unrelated = next(role for role in roles if role.label.startswith("Independiente"))
    assert unrelated.counted is False
    assert unrelated.reason == "no se relaciona con lo que pide el puesto"


@pytest.mark.parametrize(
    "title",
    [
        "Curso de Python",
        "Bootcamp Full Stack",
        "Voluntariado en una ONG",
        "Estudiante de programación",
        "Proyecto personal en Python",
        "Python training",
    ],
)
def test_courses_volunteering_and_personal_projects_are_not_jobs(title: str) -> None:
    [role] = assess_roles([_role(title, "2025-01", "2025-12")], JOB, TODAY)

    assert role.counted is False
    assert role.reason == "no es un puesto de trabajo"
    assert direct_months([role]) == 0


def test_freelance_and_independent_work_count_when_it_is_direct() -> None:
    roles = assess_roles(
        [
            _role("Desarrollador Freelance", "2025-01", "2025-12"),
            _role(
                "Python independiente", "2024-01", "2024-06", company="Independiente"
            ),
        ],
        JOB,
        TODAY,
    )

    assert direct_months(roles) == 18


def test_a_role_is_direct_when_its_text_names_a_skill_of_the_posting() -> None:
    [role] = assess_roles(
        [_role("Analista", "2025-01", "2025-06", description="Scripts en Python")],
        JOB,
        TODAY,
    )

    assert role.counted is True


def test_a_skill_inside_another_word_does_not_make_a_role_direct() -> None:
    [role] = assess_roles(
        [_role("Analista", "2025-01", "2025-06", description="Cocina pythonesca")],
        JOB,
        TODAY,
    )

    assert role.counted is False


def test_titles_match_across_spanish_and_english() -> None:
    [role] = assess_roles(
        [_role("Programadora", "2025-01", "2025-06")],
        {
            **JOB,
            "job_title": "Software Developer",
            "tech_stack": [],
            "required_skills": [],
        },
        TODAY,
    )

    assert role.counted is True


def test_a_current_role_runs_until_today() -> None:
    [role] = assess_roles(
        [_role("Python Developer", "2026-07", None, current=True)], JOB, TODAY
    )

    # Julio a octubre de 2026.
    assert role.months == 4
    assert role.counted is True


def test_a_future_end_date_is_capped_at_today() -> None:
    [role] = assess_roles([_role("Python Developer", "2026-09", "2027-12")], JOB, TODAY)

    assert role.months == 2


@pytest.mark.parametrize(
    ("started", "ended", "reason"),
    [
        (None, "2025-06", "sin fecha de inicio"),
        ("texto libre", "2025-06", "sin fecha de inicio"),
        ("2025-01", None, "sin fecha de fin"),
        ("2025-06", "2025-01", "las fechas no cierran"),
    ],
)
def test_a_role_without_usable_dates_does_not_count(
    started: str | None, ended: str | None, reason: str
) -> None:
    [role] = assess_roles([_role("Python Developer", started, ended)], JOB, TODAY)

    assert role.counted is False
    assert role.reason == reason


def test_dates_from_the_profile_table_and_from_the_reader_both_work() -> None:
    roles = assess_roles(
        [
            _role("Python Developer", "2025-01-01", "2025-03-31"),
            _role("Python Developer", "2024", "2024"),
        ],
        JOB,
        TODAY,
    )

    # Tres meses de 2025 y los doce de 2024 (un año suelto es el año entero).
    assert direct_months(roles) == 15


@pytest.mark.parametrize(
    ("months", "text"),
    [
        (0, "0 meses"),
        (1, "1 mes"),
        (6, "6 meses"),
        (12, "1 año"),
        (27, "2 años y 3 meses"),
    ],
)
def test_describing_months(months: int, text: str) -> None:
    assert describe_months(months) == text


# --- puestos de software y TI ---------------------------------------------------


def test_an_it_role_counts_for_a_software_posting_even_without_naming_the_skill() -> (
    None
):
    # El caso del autor: «IT Trainee» en una pyme, para un aviso de Python.
    [role] = assess_roles(
        [_role("IT Trainee", "2026-07", None, company="Paogi", current=True)],
        JOB,
        TODAY,
    )

    assert role.counted is True
    assert role.months == 4


def test_an_it_role_does_not_count_for_a_posting_that_is_not_software() -> None:
    kitchen = {
        "job_title": "Chef ejecutivo",
        "required_skills": ["Cocina"],
        "tech_stack": [],
    }

    [role] = assess_roles([_role("IT Trainee", "2026-01", "2026-06")], kitchen, TODAY)

    assert role.counted is False


def test_work_that_only_touches_data_or_sales_is_not_software() -> None:
    roles = assess_roles(
        [
            _role("Digital Products Operator & Data Analyst", "2024-01", "2024-10",
                  company="Remasted Shop"),
            _role("Operador y Analista Digital", "2023-01", "2023-06"),
        ],
        JOB,
        TODAY,
    )  # fmt: skip

    assert direct_months(roles) == 0


def test_an_engineer_of_another_field_is_not_a_developer() -> None:
    [role] = assess_roles(
        [_role("Ingeniero civil", "2020-01", "2022-12", company="Constructora")],
        {
            **JOB,
            "job_title": "Software Engineer",
            "tech_stack": [],
            "required_skills": [],
        },
        TODAY,
    )

    assert role.counted is False


def test_the_authors_real_roles_add_up_across_the_cv_and_linkedin() -> None:
    cv = [
        _role(
            "Desarrollador Freelance — Python & Salesforce",
            "2026-03",
            "2026-05",
            company="Pyme",
        ),
        _role("Personal", "2025-01", "2026-01", company="AutoCad Plans"),
        _role(
            "Operador y Analista Digital", "2024-01", "2024-10", company="Independiente"
        ),
    ]
    linkedin = [
        _role("IT Trainee", "2026-07", None, company="Paogi", current=True),
        _role(
            "Automation Developer — Python & Salesforce",
            "2026-03",
            "2026-04",
            company="Freelance",
        ),
        _role(
            "Digital Products Operator & Data Analyst",
            "2024-01",
            "2024-10",
            company="Remasted Shop",
        ),
    ]

    roles = assess_roles([*cv, *linkedin], JOB, TODAY)

    # Marzo a mayo (freelance) y julio a octubre (Paogi): tres y cuatro meses.
    assert direct_months(roles) == 7
    assert {role.label for role in roles if role.counted} >= {
        "Pyme — Desarrollador Freelance — Python & Salesforce",
        "Paogi — IT Trainee",
    }


# --- años pedidos ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("We need 5+ years of experience in Python.", 5),
        ("Minimum 3 years' professional experience", 3),
        ("3-5 years of relevant experience", 3),
        ("Experience: 4 years with backend systems", 4),
        ("Se requieren mínimo 2 años de experiencia en desarrollo", 2),
        ("Experiencia de 3 años en Python", 3),
    ],
)
def test_the_years_the_posting_states(raw_text: str, expected: int) -> None:
    assert required_years({"raw_text": raw_text}) == (expected, False)


def test_the_first_mention_is_the_requirement() -> None:
    job = {
        "raw_text": (
            "5+ years of experience in Python. Nice: 2 years of experience in AWS"
        )
    }

    assert required_years(job) == (5, False)


def test_a_history_of_the_company_is_not_a_requirement() -> None:
    assert required_years({"raw_text": "Our history spans over 200 years"}) == (
        None,
        False,
    )


@pytest.mark.parametrize(
    ("seniority", "expected"),
    [
        ("Senior", (5, True)),
        ("Mid", (3, True)),
        ("Staff", (8, True)),
        ("Junior", (None, False)),
    ],
)
def test_without_years_the_level_estimates_them(
    seniority: str, expected: tuple[int | None, bool]
) -> None:
    assert required_years({"raw_text": "", "required_seniority": seniority}) == expected


def test_the_years_of_the_posting_win_over_the_level() -> None:
    job = {"raw_text": "2 years of experience", "required_seniority": "Senior"}

    assert required_years(job) == (2, False)


# --- requisito de años ----------------------------------------------------------


def _experience(
    rows: list[dict[str, Any]], job: dict[str, Any] = JOB
) -> ATSRequirement:
    [requirement] = [
        item
        for item in evaluate_requirements(
            job, experiences=rows, educations=[], languages=[], today=TODAY
        )
        if item.key == "experience"
    ]
    return requirement


def test_six_direct_months_against_a_senior_posting_is_unmet_but_not_zero_credit() -> (
    None
):
    requirement = _experience(
        [
            _role("Desarrollador Python", "2026-01", "2026-03"),
            _role("Python Developer", "2026-07", "2026-09"),
        ]
    )

    assert requirement.required == "5 años (según el nivel del puesto)"
    assert requirement.estimated is True
    assert requirement.actual == "6 meses"
    assert requirement.status == "unmet"
    assert requirement.ratio == pytest.approx(0.1)
    # Se muestra qué puestos se tuvieron en cuenta.
    assert len(requirement.detail) == 2


def test_the_detail_says_why_a_role_does_not_count() -> None:
    requirement = _experience(
        [
            _role("Python Developer", "2026-07", "2026-09", company="Paogi"),
            _role("Curso de Excel", "2025-01", "2025-12"),
        ]
    )

    assert "Paogi — Python Developer: 3 meses" in requirement.detail
    assert (
        "Curso de Excel: no cuenta (no es un puesto de trabajo)" in requirement.detail
    )


def test_half_of_the_years_is_partial() -> None:
    job = {**JOB, "raw_text": "4 years of experience"}

    requirement = _experience([_role("Python Developer", "2024-11", "2026-10")], job)

    assert requirement.status == "partial"
    assert requirement.ratio == pytest.approx(0.5)


def test_meeting_the_years_exactly_is_met_without_a_note() -> None:
    job = {**JOB, "raw_text": "2 years of experience"}

    requirement = _experience([_role("Python Developer", "2024-11", "2026-10")], job)

    assert requirement.status == "met"
    assert requirement.ratio == 1.0
    assert requirement.note is None


def test_exceeding_the_years_is_met_and_only_leaves_a_note() -> None:
    job = {**JOB, "raw_text": "2 years of experience"}

    requirement = _experience([_role("Python Developer", "2020-01", "2026-10")], job)

    assert requirement.status == "met"
    assert requirement.ratio == 1.0
    assert requirement.note is not None
    assert "Superás lo pedido" in requirement.note
    assert "no suma ni resta" in requirement.note


def test_a_little_over_the_years_does_not_deserve_a_note() -> None:
    job = {**JOB, "raw_text": "2 years of experience"}

    requirement = _experience([_role("Python Developer", "2024-04", "2026-10")], job)

    assert requirement.ratio == 1.0
    assert requirement.note is None


def test_a_posting_without_years_or_level_asks_nothing() -> None:
    assert (
        evaluate_requirements(
            {"job_title": "Dev", "raw_text": "Nice team"},
            experiences=[],
            educations=[],
            languages=[],
            today=TODAY,
        )
        == []
    )


def test_a_person_without_any_experience_gets_zero_for_the_years() -> None:
    requirement = _experience([])

    assert requirement.ratio == 0.0
    assert requirement.status == "unmet"
    assert requirement.actual == "0 meses"


# --- formación ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "rank"),
    [
        ("Tecnico Informatico", 2),
        ("Tecnicatura en Programación", 2),
        ("Licenciatura en Sistemas", 3),
        ("Ingeniería en Sistemas", 3),
        ("Lic. en Informática", 3),
        ("Universidad de Buenos Aires", 3),
        ("Bachelor's degree", 3),
        ("Undergraduate degree or equivalent experience", 3),
        ("Master in Data Science", 4),
        ("Maestría en Datos", 4),
        ("PhD in Physics", 5),
        ("Secundario completo", 1),
        ("Excel Basics", 0),
    ],
)
def test_the_education_level_a_text_names(text: str, rank: int) -> None:
    assert education_rank(text) == rank


def _education(required: str, rows: list[dict[str, Any]]) -> ATSRequirement | None:
    found = [
        item
        for item in evaluate_requirements(
            {"required_education": required},
            experiences=[],
            educations=rows,
            languages=[],
            today=TODAY,
        )
        if item.key == "education"
    ]
    return found[0] if found else None


def test_the_same_level_is_met() -> None:
    requirement = _education(
        "Bachelor's degree", [{"institution": "UTN", "field_of_study": "Ingeniería"}]
    )

    assert requirement is not None
    assert requirement.status == "met"
    assert requirement.note is None


def test_a_higher_degree_is_met_with_a_note_that_does_not_move_the_score() -> None:
    requirement = _education(
        "Bachelor's degree", [{"institution": "UBA", "degree_level": "Master"}]
    )

    assert requirement is not None
    assert requirement.ratio == 1.0
    assert requirement.note == "Superás lo pedido: no suma ni resta puntos."


def test_one_level_below_is_partial() -> None:
    requirement = _education(
        "Bachelor's degree", [{"institution": "Escuela", "field_of_study": "Técnico"}]
    )

    assert requirement is not None
    assert requirement.status == "partial"
    assert requirement.ratio == pytest.approx(0.75)


def test_equivalent_experience_gives_at_least_half() -> None:
    requirement = _education(
        "Undergraduate degree or equivalent experience",
        [{"institution": "Escuela", "field_of_study": "Técnico", "is_ongoing": True}],
    )

    assert requirement is not None
    assert requirement.ratio >= 0.5
    assert requirement.note is not None
    assert "experiencia equivalente" in requirement.note


def test_without_any_education_a_strict_requirement_is_unmet() -> None:
    requirement = _education("Bachelor's degree", [])

    assert requirement is not None
    assert requirement.status == "unmet"
    assert requirement.ratio == 0.0


def test_without_education_an_equivalent_experience_posting_still_gives_half() -> None:
    requirement = _education("Degree or equivalent experience", [])

    assert requirement is not None
    assert requirement.ratio == 0.5


def test_a_degree_in_progress_counts_half() -> None:
    requirement = _education(
        "Bachelor's degree",
        [{"institution": "UBA", "field_of_study": "Licenciatura", "is_ongoing": True}],
    )

    assert requirement is not None
    assert requirement.ratio == 0.5
    assert requirement.actual.endswith("en curso")


def test_a_finished_degree_wins_over_one_in_progress_of_the_same_level() -> None:
    requirement = _education(
        "Bachelor's degree",
        [
            {
                "institution": "UBA",
                "field_of_study": "Licenciatura",
                "is_ongoing": True,
            },
            {"institution": "UTN", "field_of_study": "Ingeniería", "is_ongoing": False},
        ],
    )

    assert requirement is not None
    assert requirement.ratio == 1.0


def test_courses_are_not_a_formal_education() -> None:
    requirement = _education(
        "Bachelor's degree",
        [{"institution": "Coursera IBM", "field_of_study": "Excel Basics"}],
    )

    assert requirement is not None
    assert requirement.ratio == 0.0


def test_a_requirement_text_without_a_known_level_asks_nothing() -> None:
    assert _education("Se valora la curiosidad", [{"institution": "UTN"}]) is None
    assert _education("", [{"institution": "UTN"}]) is None


# --- idiomas --------------------------------------------------------------------


def _languages(required: list[Any], rows: list[dict[str, Any]]) -> list[ATSRequirement]:
    return [
        item
        for item in evaluate_requirements(
            {"required_languages": required},
            experiences=[],
            educations=[],
            languages=rows,
            today=TODAY,
        )
        if item.key.startswith("language:")
    ]


def test_english_and_ingles_are_the_same_language() -> None:
    [requirement] = _languages(
        ["English"], [{"name": "Inglés", "proficiency": "intermediate"}]
    )

    assert requirement.key == "language:english"
    assert requirement.label == "Inglés"
    assert requirement.status == "met"
    assert requirement.ratio == 1.0
    assert requirement.required == "nivel no indicado"


def test_a_better_level_than_asked_is_met_with_a_note() -> None:
    [requirement] = _languages(
        [{"name": "English", "level": "intermediate"}],
        [{"name": "Inglés", "proficiency": "native"}],
    )

    assert requirement.ratio == 1.0
    assert requirement.note == "Superás lo pedido: no suma ni resta puntos."


def test_a_lower_level_is_partial_by_the_steps_missing() -> None:
    [requirement] = _languages(
        [{"name": "English", "level": "advanced"}],
        [{"name": "English", "proficiency": "intermediate"}],
    )

    assert requirement.status == "partial"
    assert requirement.ratio == pytest.approx(0.75)
    assert requirement.required == "avanzado"


def test_a_language_the_person_does_not_list_is_unmet() -> None:
    [requirement] = _languages(
        ["English"], [{"name": "Español", "proficiency": "native"}]
    )

    assert requirement.status == "unmet"
    assert requirement.ratio == 0.0


def test_the_best_level_wins_when_the_language_is_listed_twice() -> None:
    [requirement] = _languages(
        [{"name": "English", "level": "advanced"}],
        [
            {"name": "English", "level": "basic"},
            {"name": "Inglés", "proficiency": "advanced"},
        ],
    )

    assert requirement.ratio == 1.0


def test_each_required_language_is_its_own_requirement_without_repeats() -> None:
    result = _languages(
        ["English", "Inglés", "Portuguese"],
        [{"name": "English", "proficiency": "advanced"}],
    )

    assert [item.key for item in result] == ["language:english", "language:portuguese"]


# --- puntaje ---------------------------------------------------------------------


def _match(status: str) -> ATSKeywordMatch:
    return ATSKeywordMatch(keyword=status, status=status)  # type: ignore[arg-type]


def _requirement(key: str, ratio: float) -> ATSRequirement:
    return ATSRequirement(
        key=key, label=key, required="", actual="", status="met", ratio=ratio
    )


def test_without_requirements_the_score_is_the_keyword_coverage() -> None:
    matches = [
        _match("literal"),
        _match("semantic"),
        _match("missing"),
        _match("missing"),
    ]

    assert keyword_coverage(matches) == pytest.approx(0.375)
    assert compose_ats_score(matches) == 38
    assert compose_ats_score(matches, []) == 38


def test_the_weights_are_shared_among_what_the_posting_asks() -> None:
    matches = [_match("literal"), _match("missing")]
    requirements = [
        _requirement("experience", 1.0),
        _requirement("education", 0.0),
        _requirement("language:english", 1.0),
    ]

    # Skills 60 × 0,5 + años 20 × 1 + formación 10 × 0 + idioma 10 × 1 = 60 de 100.
    assert compose_ats_score(matches, requirements) == 60


def test_the_language_weight_is_split_among_the_languages() -> None:
    matches = [_match("literal")]
    requirements = [
        _requirement("language:english", 1.0),
        _requirement("language:french", 0.0),
    ]

    # Skills 60 × 1 + inglés 5 × 1 + francés 5 × 0 = 65 de 70.
    assert compose_ats_score(matches, requirements) == 93


def test_exceeding_a_requirement_adds_nothing_to_the_score() -> None:
    matches = [_match("literal"), _match("missing")]
    exact = _requirement("experience", 1.0)
    exceeded = ATSRequirement(
        key="experience",
        label="x",
        required="",
        actual="",
        status="met",
        ratio=1.0,
        note="Superás lo pedido: no suma ni resta puntos.",
    )

    assert compose_ats_score(matches, [exact]) == compose_ats_score(matches, [exceeded])


def test_nothing_to_evaluate_scores_a_hundred() -> None:
    assert compose_ats_score([], []) == 100


def test_the_score_never_falls_to_zero_for_a_partial_profile() -> None:
    # El caso que motivó el cambio: una keyword de ocho y el resto de lo que pide el
    # puesto cubierto en parte. Antes daba 0 por restarle el formato.
    matches = [_match("literal"), *[_match("missing") for _ in range(7)]]
    requirements = [
        _requirement("experience", 0.1),
        _requirement("education", 0.5),
        _requirement("language:english", 1.0),
    ]

    # (60 × 0,125 + 20 × 0,1 + 10 × 0,5 + 10 × 1) / 100 = 24,5 -> 24.
    assert compose_ats_score(matches, requirements) == 24
