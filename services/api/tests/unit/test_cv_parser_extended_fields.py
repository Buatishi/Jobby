"""El lector de CV guarda lo que antes descartaba (Decisión 41).

Medido el 2026-10-31 en el CV de una cuenta real: de cada experiencia solo quedaban la
empresa, el cargo, la fecha de inicio y un párrafo con todas las viñetas pegadas; de
cada estudio, el título y la institución; de cada certificado, el nombre y quién lo
emite. Sin fecha de fin, sin «actualidad» y sin fechas de estudios, el CV descargable
no podía salir completo. Los datos de acá son inventados.

Lo que más importa es que un campo nuevo nunca haga fallar el análisis de un CV: la IA
devuelve nulos, objetos y formatos inesperados (PR #124), y un CV sin los campos nuevos
tiene que validar igual que antes.
"""

import json
from typing import Any

import pytest

from app.services.ats_analyzer.keyword_matcher import analyze_keywords
from app.services.cv_parser import ai_structurer
from app.services.cv_parser.ai_structurer import (
    CVStructuredData,
    _normalize_structured_payload,
)
from app.services.cv_parser.merge_logic import merge_structured_cv_data
from app.services.match_engine.common import experiences_with_text
from app.services.match_engine.s_relevance import build_profile_text, compute_relevance
from app.services.match_engine.s_soft import compute_soft_score, infer_soft_skills
from app.services.printable_cv import build_printable_cv
from app.tasks import parsing


def _experience(**fields: Any) -> dict[str, Any]:
    normalized = _normalize_structured_payload(
        {
            "experiences": [
                {"company": "Distribuidora Andina", "title": "Analista", **fields}
            ]
        }
    )
    return normalized["experiences"][0]  # type: ignore[no-any-return]


def _education(**fields: Any) -> dict[str, Any]:
    normalized = _normalize_structured_payload(
        {"educations": [{"institution": "Escuela Técnica", **fields}]}
    )
    return normalized["educations"][0]  # type: ignore[no-any-return]


def _certification(**fields: Any) -> dict[str, Any]:
    normalized = _normalize_structured_payload(
        {"certifications": [{"name": "Análisis de Datos", **fields}]}
    )
    return normalized["certifications"][0]  # type: ignore[no-any-return]


# --- experiencias: fin de la fecha y «actualidad» -------------------------------------


def test_an_experience_keeps_when_it_started_and_when_it_ended() -> None:
    experience = _experience(started_at="Julio 2024", ended_at="Marzo 2025")

    assert experience["started_at"] == "2024-07"
    assert experience["ended_at"] == "2025-03"
    assert experience["is_current"] is False


def test_an_experience_that_continues_has_no_end_and_is_current() -> None:
    experience = _experience(started_at="Julio 2026", ended_at="Presente")

    assert experience["started_at"] == "2026-07"
    assert experience["ended_at"] == ""
    assert experience["is_current"] is True


def test_the_flag_without_an_end_date_also_means_current() -> None:
    assert _experience(started_at="2026", is_current=True)["is_current"] is True


def test_a_period_written_in_one_field_is_split() -> None:
    experience = _experience(started_at="Julio 2026 - Actualidad")

    assert (experience["started_at"], experience["ended_at"]) == ("2026-07", "")
    assert experience["is_current"] is True


def test_the_usual_aliases_of_the_ai_are_read() -> None:
    experience = _experience(start_date="Mar 2020", end_date="Dic 2021", current="no")

    assert (experience["started_at"], experience["ended_at"]) == ("2020-03", "2021-12")
    assert experience["is_current"] is False


# --- experiencias: una viñeta por elemento --------------------------------------------


def test_each_bullet_stays_as_its_own_element() -> None:
    experience = _experience(
        achievements=["Armé tableros en Power BI", "Automaticé reportes en Python"]
    )

    assert experience["achievements"] == [
        "Armé tableros en Power BI",
        "Automaticé reportes en Python",
    ]


def test_bullets_written_as_one_text_are_split_by_line_and_marker() -> None:
    experience = _experience(
        achievements=(
            "• Armé tableros en Power BI\n- Automaticé reportes\n· Capacité al equipo"
        )
    )

    assert experience["achievements"] == [
        "Armé tableros en Power BI",
        "Automaticé reportes",
        "Capacité al equipo",
    ]


def test_a_bullet_with_line_breaks_inside_a_list_is_split_too() -> None:
    experience = _experience(achievements=["* Armé tableros\n* Automaticé reportes"])

    assert experience["achievements"] == ["Armé tableros", "Automaticé reportes"]


def test_a_sentence_with_a_hyphen_or_a_middle_dot_inside_is_not_split() -> None:
    sentences = [
        "Migré el back-end a Python 3 - sin cortes",
        "Stack: Python · FastAPI · PostgreSQL",
    ]

    assert _experience(achievements=sentences)["achievements"] == sentences


def test_bullets_given_as_objects_numbers_or_nested_lists_are_read() -> None:
    experience = _experience(
        achievements=[
            {"text": "Armé tableros"},
            {"description": "Automaticé reportes"},
            {"name": "Capacité al equipo"},
            ["Documenté procesos", None, ""],
            42,
            3.5,
            {"unexpected": ["x"]},
            None,
            True,
        ]
    )

    assert experience["achievements"] == [
        "Armé tableros",
        "Automaticé reportes",
        "Capacité al equipo",
        "Documenté procesos",
    ]


def test_blank_and_repeated_bullets_are_dropped_and_the_order_is_kept() -> None:
    experience = _experience(
        achievements=["Armé tableros", "  ", "armé tableros.", "Automaticé reportes"]
    )

    assert experience["achievements"] == ["Armé tableros", "Automaticé reportes"]


@pytest.mark.parametrize("value", [None, "", [], {}, 0, False, [None, "", "  "]])
def test_no_bullets_leaves_the_list_empty(value: Any) -> None:
    assert _experience(achievements=value)["achievements"] == []


def test_a_single_string_without_markers_is_one_bullet() -> None:
    """Es el comportamiento de antes, y lo fija otra prueba del lector."""
    assert _experience(achievements="Reduced latency")["achievements"] == [
        "Reduced latency"
    ]


# --- experiencias: la descripción no repite las viñetas -------------------------------

INTRO = "Analista en el área de datos."
BULLETS = [
    "Armé tableros en Power BI para ventas.",
    "Automaticé reportes semanales con Python.",
    "Capacité a tres compañeros en SQL.",
]


def test_a_description_that_repeats_the_bullets_keeps_only_what_they_do_not_say() -> (
    None
):
    """La web muestra la descripción en viñetas y después los logros: repetidos se leen
    dos veces en el PDF."""
    experience = _experience(
        description=f"{INTRO} {' '.join(BULLETS)}", achievements=BULLETS
    )

    assert experience["description"] == INTRO
    assert experience["achievements"] == BULLETS


def test_a_description_made_only_of_the_bullets_is_emptied() -> None:
    experience = _experience(description="\n".join(BULLETS), achievements=BULLETS)

    assert experience["description"] == ""


def test_the_repeat_is_found_whatever_the_case_markers_and_accents() -> None:
    experience = _experience(
        description="• ARMÉ TABLEROS EN POWER BI PARA VENTAS\n• automatice reportes "
        "semanales con python\nResponsable del área.",
        achievements=BULLETS,
    )

    assert experience["description"] == "Responsable del área."


def test_a_bullet_of_two_sentences_removes_each_sentence_from_the_description() -> None:
    experience = _experience(
        description="Reduje la latencia un 30%. Agregué caché. Fui guardia rotativo.",
        achievements=["Reduje la latencia un 30%. Agregué caché."],
    )

    assert experience["description"] == "Fui guardia rotativo."


def test_a_description_that_only_shares_a_phrase_with_a_bullet_is_kept() -> None:
    """No se corta la mitad de una oración: solo se saca la que coincide entera."""
    description = "Lideré la migración a Kubernetes en el equipo de plataforma."
    experience = _experience(
        description=description, achievements=["Lideré la migración a Kubernetes"]
    )

    assert experience["description"] == description


def test_a_description_is_untouched_when_there_are_no_bullets() -> None:
    description = f"{INTRO} {' '.join(BULLETS)}"

    assert _experience(description=description)["description"] == description


def test_a_description_that_is_exactly_a_bullet_is_emptied() -> None:
    experience = _experience(description="Docker", achievements=["Docker"])

    assert experience["description"] == ""
    assert experience["achievements"] == ["Docker"]


# --- estudios -------------------------------------------------------------------------


def test_an_education_keeps_its_dates() -> None:
    education = _education(
        degree_level="bachelor", started_at="Marzo 2018", ended_at="Diciembre 2022"
    )

    assert education["started_at"] == "2018-03"
    assert education["ended_at"] == "2022-12"
    assert education["is_ongoing"] is False


@pytest.mark.parametrize("marker", ["En curso", "Cursando", "Presente", "In progress"])
def test_a_study_still_going_is_ongoing_and_has_no_end(marker: str) -> None:
    education = _education(started_at="2023", ended_at=marker)

    assert education["ended_at"] == ""
    assert education["is_ongoing"] is True


def test_the_graduation_year_alone_is_the_end() -> None:
    education = _education(graduation_date="2022")

    assert (education["started_at"], education["ended_at"]) == ("", "2022")
    assert education["is_ongoing"] is False


def test_the_flag_of_an_education_is_read_with_its_aliases() -> None:
    assert _education(ongoing=True)["is_ongoing"] is True
    assert _education(in_progress="true")["is_ongoing"] is True
    assert _education(is_ongoing="false")["is_ongoing"] is False


def test_an_education_period_in_one_field_is_split() -> None:
    education = _education(started_at="2019 - 2022")

    assert (education["started_at"], education["ended_at"]) == ("2019", "2022")


def test_an_education_with_only_dates_is_still_dropped() -> None:
    normalized = _normalize_structured_payload(
        {"educations": [{"started_at": "2019", "ended_at": "2022"}]}
    )

    assert normalized["educations"] == []


# --- certificados ---------------------------------------------------------------------


def test_a_certification_keeps_when_it_was_issued() -> None:
    assert _certification(issued_at="Mayo 2024")["issued_at"] == "2024-05"


@pytest.mark.parametrize("key", ["issue_date", "date", "year", "obtained_at"])
def test_the_usual_aliases_of_the_issue_date_are_read(key: str) -> None:
    assert _certification(**{key: "2023"})["issued_at"] == "2023"


def test_a_certification_without_a_date_has_it_empty() -> None:
    assert _certification()["issued_at"] == ""


def test_a_certification_given_as_a_plain_string_has_no_date() -> None:
    normalized = _normalize_structured_payload({"certifications": ["AWS Practitioner"]})

    assert normalized["certifications"][0] == {
        "name": "AWS Practitioner",
        "issuer": "",
        "issued_at": "",
    }


# --- un CV sin los campos nuevos valida igual que antes ------------------------------


def test_a_payload_without_the_new_fields_validates_and_has_them_empty() -> None:
    payload = {
        "contact": {"full_name": "Lucía Ferreyra"},
        "skills": [{"name": "Python", "category": "technical", "level": "advanced"}],
        "experiences": [
            {
                "company": "Distribuidora Andina",
                "title": "Analista",
                "started_at": "Julio 2026",
                "description": "Reportes semanales.",
                "achievements": ["Armé tableros"],
            }
        ],
        "educations": [{"institution": "Escuela Técnica", "degree_level": "technical"}],
        "languages": [{"name": "Inglés", "level": "intermediate"}],
        "certifications": [{"name": "Análisis de Datos", "issuer": "Coursera"}],
    }

    parsed = CVStructuredData.model_validate(_normalize_structured_payload(payload))

    experience = parsed.experiences[0]
    assert (experience.company, experience.title) == (
        "Distribuidora Andina",
        "Analista",
    )
    assert experience.description == "Reportes semanales."
    assert experience.achievements == ["Armé tableros"]
    assert not experience.ended_at
    assert experience.is_current is False
    assert not parsed.educations[0].started_at
    assert parsed.educations[0].is_ongoing is False
    assert not parsed.certifications[0].issued_at


def test_the_models_can_still_be_built_without_the_new_fields() -> None:
    data = CVStructuredData.model_validate(
        {
            "experiences": [{"company": "Acme", "title": "Dev"}],
            "educations": [{"institution": "UBA"}],
            "certifications": [{"name": "AWS"}],
        }
    )

    assert data.experiences[0].ended_at is None
    assert data.experiences[0].is_current is False
    assert data.educations[0].is_ongoing is False
    assert data.certifications[0].issued_at is None


# --- ningún valor de la IA hace fallar el análisis ------------------------------------


def _case_id(value: Any) -> str:
    return f"{type(value).__name__}-{len(str(value))}"


HOSTILE = [
    None,
    "",
    "   ",
    0,
    1,
    -1,
    3.14,
    float("inf"),
    float("nan"),
    1e308,
    10**400,
    -(10**400),
    True,
    False,
    [],
    [None],
    ["a", {"b": ["c"]}],
    {},
    {"nested": {"deep": [None, {"x": 1}]}},
    {"year": {"x": 1}, "month": [1]},
    "x" * 10_000,
    "\x00\ud800",
    "Presente\n" * 50,
]


@pytest.mark.parametrize("value", HOSTILE, ids=_case_id)
def test_any_value_in_any_new_field_validates(value: Any) -> None:
    payload = {
        "experiences": [
            {
                "company": "Acme",
                "title": "Dev",
                "started_at": value,
                "ended_at": value,
                "is_current": value,
                "description": value,
                "achievements": value,
            }
        ],
        "educations": [
            {
                "institution": "UBA",
                "started_at": value,
                "ended_at": value,
                "is_ongoing": value,
            }
        ],
        "certifications": [{"name": "AWS", "issued_at": value}],
    }

    parsed = CVStructuredData.model_validate(_normalize_structured_payload(payload))

    assert parsed.experiences[0].company == "Acme"
    assert parsed.educations[0].institution == "UBA"
    assert parsed.certifications[0].name == "AWS"


@pytest.mark.parametrize("value", HOSTILE, ids=_case_id)
def test_the_new_fields_always_come_out_as_text_and_booleans(value: Any) -> None:
    experience = _experience(ended_at=value, is_current=value, achievements=value)
    education = _education(ended_at=value, is_ongoing=value)
    certification = _certification(issued_at=value)

    assert isinstance(experience["ended_at"], str)
    assert isinstance(experience["is_current"], bool)
    assert all(isinstance(item, str) for item in experience["achievements"])
    assert isinstance(education["ended_at"], str)
    assert isinstance(education["is_ongoing"], bool)
    assert isinstance(certification["issued_at"], str)


class _Reply:
    def __init__(self, content: str) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"choices": [{"message": {"content": self.content}}]}


def _fake_deepseek(
    monkeypatch: pytest.MonkeyPatch, content: str
) -> list[dict[str, Any]]:
    """Reemplaza la llamada a DeepSeek y devuelve los pedidos que se le hicieron."""
    requests: list[dict[str, Any]] = []

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, _url: str, **kwargs: Any) -> _Reply:
            requests.append(kwargs["json"])
            return _Reply(content)

    monkeypatch.setattr(ai_structurer.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(ai_structurer.httpx, "AsyncClient", FakeClient)
    return requests


@pytest.mark.asyncio
async def test_a_reply_full_of_unexpected_values_is_read_in_one_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Con un campo nuevo mal formado no hay reintento ni error: el CV se analiza."""
    reply = json.dumps(
        {
            "contact": {},
            "skills": ["Python"],
            "experiences": [
                {
                    "company": "Acme",
                    "title": "Dev",
                    "started_at": {"month": "July", "year": 2026},
                    "ended_at": None,
                    "is_current": "sí",
                    "description": None,
                    "achievements": {"unexpected": ["Armé tableros"]},
                }
            ],
            "educations": [
                {"institution": "UBA", "started_at": 2018, "ended_at": ["2022"]}
            ],
            "certifications": [{"name": "AWS", "issued_at": {"when": 2024}}],
        }
    )
    requests = _fake_deepseek(monkeypatch, reply)

    parsed = await ai_structurer.structure_cv_text("Python")

    assert len(requests) == 1
    experience = parsed.experiences[0]
    assert experience.started_at == "2026-07"
    assert experience.is_current is True
    assert experience.achievements == []
    assert parsed.educations[0].started_at == "2018"
    assert not parsed.educations[0].ended_at
    assert not parsed.certifications[0].issued_at


@pytest.mark.asyncio
async def test_a_complete_reply_comes_out_with_every_new_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reply = json.dumps(
        {
            "contact": {"full_name": "Lucía Ferreyra"},
            "skills": [
                {"name": "Python", "category": "technical", "level": "advanced"}
            ],
            "experiences": [
                {
                    "company": "Distribuidora Andina",
                    "title": "Analista de datos",
                    "started_at": "Julio 2026",
                    "ended_at": "Presente",
                    "is_current": True,
                    "description": INTRO,
                    "achievements": BULLETS,
                }
            ],
            "educations": [
                {
                    "institution": "Escuela Técnica",
                    "field_of_study": "Programación",
                    "degree_level": "technical",
                    "started_at": "2023",
                    "ended_at": "En curso",
                    "is_ongoing": True,
                }
            ],
            "certifications": [
                {
                    "name": "Análisis de Datos",
                    "issuer": "Coursera",
                    "issued_at": "Mayo 2024",
                }
            ],
        }
    )
    _fake_deepseek(monkeypatch, reply)

    stored = merge_structured_cv_data(await ai_structurer.structure_cv_text("cv"), [])

    assert stored["experiences"] == [
        {
            "company": "Distribuidora Andina",
            "title": "Analista de datos",
            "started_at": "2026-07",
            "ended_at": "",
            "is_current": True,
            "description": INTRO,
            "achievements": BULLETS,
        }
    ]
    assert stored["educations"] == [
        {
            "institution": "Escuela Técnica",
            "field_of_study": "Programación",
            "degree_level": "technical",
            "started_at": "2023",
            "ended_at": "",
            "is_ongoing": True,
        }
    ]
    assert stored["certifications"] == [
        {"name": "Análisis de Datos", "issuer": "Coursera", "issued_at": "2024-05"}
    ]


# --- el prompt ------------------------------------------------------------------------


def test_the_prompt_defines_the_new_fields_and_how_to_fill_them() -> None:
    prompt = ai_structurer._system_prompt()

    assert (
        "experiences {company, title, started_at, ended_at, is_current, "
        "description, achievements}"
    ) in prompt
    assert (
        "educations {institution, field_of_study, degree_level, started_at, "
        "ended_at, is_ongoing}"
    ) in prompt
    assert "certifications {name, issuer, issued_at}" in prompt
    assert "exactly as the CV writes it" in prompt
    assert "achievements" in prompt
    assert "never repeat" in prompt.lower()


def test_the_prompt_asks_for_booleans_and_still_forbids_null_text() -> None:
    prompt = ai_structurer._user_prompt("texto")

    assert "is_current" in prompt and "is_ongoing" in prompt
    assert "true or false" in prompt
    assert "never null" in prompt


def test_the_prompt_stays_inside_the_token_budget_of_the_decision() -> None:
    """Antes eran 1326 caracteres (~330 tokens). La Decisión 41 acepta hasta ~1900."""
    size = len(ai_structurer._system_prompt()) + len(ai_structurer._user_prompt(""))

    assert size <= 1_900


# --- los datos llegan a donde se guardan y se leen ------------------------------------


def _data() -> CVStructuredData:
    return CVStructuredData.model_validate(
        _normalize_structured_payload(
            {
                "experiences": [
                    {
                        "company": "Distribuidora Andina",
                        "title": "Analista",
                        "started_at": "Julio 2026",
                        "ended_at": "Presente",
                        "achievements": BULLETS,
                    }
                ],
                "educations": [
                    {
                        "institution": "Escuela Técnica",
                        "started_at": "2023",
                        "ended_at": "En curso",
                    }
                ],
                "certifications": [
                    {"name": "Análisis de Datos", "issued_at": "Mayo 2024"}
                ],
            }
        )
    )


def test_the_new_fields_are_stored_in_parsed_data_for_a_cv() -> None:
    stored = merge_structured_cv_data(_data(), [])

    assert stored["experiences"][0]["is_current"] is True
    assert stored["experiences"][0]["started_at"] == "2026-07"
    assert stored["educations"][0]["is_ongoing"] is True
    assert stored["certifications"][0]["issued_at"] == "2024-05"


def test_the_new_fields_are_stored_in_parsed_data_for_a_linkedin_document() -> None:
    stored = parsing._structured_sections(_data())

    assert stored["experiences"][0]["is_current"] is True
    assert stored["educations"][0]["ended_at"] == ""
    assert stored["certifications"][0]["issued_at"] == "2024-05"


def test_the_downloadable_cv_reads_what_the_reader_stored() -> None:
    stored = merge_structured_cv_data(_data(), [])

    cv = build_printable_cv(
        profile={"headline": None, "linkedin_url": None},
        primary_cv={"parsed_data": stored},
        account_email="cuenta@example.com",
        skills=[],
        experiences=[],
        educations=[],
        languages=[],
        certifications=[],
    )

    experience = cv.experiences[0]
    assert (experience.started_at, experience.ended_at) == ("2026-07", None)
    assert experience.is_current is True
    assert experience.achievements == BULLETS


def test_the_downloadable_cv_orders_the_jobs_by_the_stored_dates() -> None:
    """Con el texto del CV («Septiembre 2024» > «Marzo 2025» > «Julio 2026» como texto)
    el orden salía por el nombre del mes y no por la fecha."""
    payload = {
        "experiences": [
            {"company": "A", "title": "Primero", "started_at": "Septiembre 2024"},
            {"company": "B", "title": "Tercero", "started_at": "Julio 2026"},
            {"company": "C", "title": "Segundo", "started_at": "Marzo 2025"},
        ]
    }
    stored = merge_structured_cv_data(
        CVStructuredData.model_validate(_normalize_structured_payload(payload)), []
    )

    cv = build_printable_cv(
        profile={"headline": None, "linkedin_url": None},
        primary_cv={"parsed_data": stored},
        account_email="cuenta@example.com",
        skills=[],
        experiences=[],
        educations=[],
        languages=[],
        certifications=[],
    )

    assert [item.title for item in cv.experiences] == ["Tercero", "Segundo", "Primero"]


def test_experiences_stored_with_the_new_fields_still_count_as_text() -> None:
    stored = merge_structured_cv_data(_data(), [])
    primary_cv = {"type": "cv", "is_primary": True, "parsed_data": stored}

    rows = experiences_with_text(
        [{"title": "Analista", "description": ""}], [primary_cv]
    )

    assert rows[0]["achievements"] == BULLETS


# --- los puntajes no se mueven por repartir el texto entre descripción y logros -------

PARAGRAPH = (
    "Desarrollé APIs REST con Python y FastAPI. "
    "Reduje la latencia de las consultas con índices en PostgreSQL. "
    "Trabajo colaborativo en equipo con diseño y datos. "
    "Resolución de incidencias en producción."
)
SENTENCES = [sentence.strip() for sentence in PARAGRAPH.split(". ") if sentence.strip()]


def _old_shape() -> dict[str, Any]:
    """Lo que el lector guardaba: todo en un párrafo y los logros vacíos."""
    return _experience(description=f"Backend en una fintech. {PARAGRAPH}")


def _new_shape() -> dict[str, Any]:
    """Lo que guarda ahora, aunque la IA repita las viñetas en la descripción."""
    return _experience(
        description=f"Backend en una fintech. {PARAGRAPH}", achievements=SENTENCES
    )


def test_the_new_shape_has_the_same_words_split_between_description_and_bullets() -> (
    None
):
    old, new = _old_shape(), _new_shape()

    assert new["description"] == "Backend en una fintech."
    assert len(new["achievements"]) == 4
    assert old["achievements"] == []

    def words(experience: dict[str, Any]) -> set[str]:
        text = " ".join([experience["description"], *experience["achievements"]])
        return set(text.lower().replace(".", "").split())

    assert words(old) == words(new)


def test_the_soft_skills_are_the_same_in_both_shapes() -> None:
    job = {"soft_skills": ["Teamwork", "Resolución de problemas"]}

    old = compute_soft_score({}, [_old_shape()], job)
    new = compute_soft_score({}, [_new_shape()], job)

    assert infer_soft_skills([_old_shape()]) == infer_soft_skills([_new_shape()])
    assert old == new


def test_the_relevance_is_the_same_in_both_shapes() -> None:
    job = {"required_skills": ["Python", "FastAPI", "PostgreSQL", "Kubernetes"]}
    results = []
    for experience in (_old_shape(), _new_shape()):
        text = build_profile_text({}, [], [experience])
        results.append(compute_relevance([], job, {"score": 0.0}, text))

    assert results[0] == results[1]
    assert results[0]["evidence"] == 0.75


class _OneHotGateway:
    """Cada texto distinto tiene su propio vector: lo que no coincide por texto tampoco
    por significado. Mide solo la parte literal del ATS."""

    def __init__(self) -> None:
        self.axes: dict[str, int] = {}
        self.embedded = 0

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        self.embedded += len(texts)
        vectors = []
        for text in texts:
            axis = self.axes.setdefault(text.lower(), len(self.axes))
            vectors.append([1.0 if axis == i else 0.0 for i in range(256)])
        return vectors


async def _ats(experience: dict[str, Any]) -> tuple[dict[str, str], int]:
    keywords = ["Python", "FastAPI", "PostgreSQL", "Kubernetes", "Trabajo colaborativo"]
    gateway = _OneHotGateway()
    cv = {"parsed_data": {"skills": [{"name": "SQL"}], "experiences": [experience]}}
    result = await analyze_keywords(
        {},
        cv,
        gateway=gateway,
        keywords=keywords,  # type: ignore[arg-type]
    )
    return {m.keyword: m.status for m in result.matches}, gateway.embedded


@pytest.mark.asyncio
async def test_the_ats_literal_matches_are_the_same_in_both_shapes() -> None:
    old, _ = await _ats(_old_shape())
    new, _ = await _ats(_new_shape())

    assert old == new
    assert old["Python"] == "literal"
    assert old["Kubernetes"] == "missing"


@pytest.mark.asyncio
async def test_the_ats_embeds_more_and_shorter_terms_with_bullets() -> None:
    """Lo único que cambia: el ATS compara por significado cada viñeta, no el párrafo.
    No se puede medir el efecto en el puntaje sin los vectores reales (Decisión 41)."""
    _, with_paragraph = await _ats(_old_shape())
    _, with_bullets = await _ats(_new_shape())

    assert with_bullets > with_paragraph
