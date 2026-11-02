"""Palabras clave obligatorias y deseables en el reporte ATS (Decisión 42).

El aviso suele separar lo que pide de lo que «se valora» o es «nice to have». Una
palabra deseable que falta no debería pesar como una obligatoria, ni una que figura
sumar lo mismo. La prioridad se guarda dentro de cada palabra del reporte (ya es
JSON): sin migración, y un reporte de antes se lee como todas obligatorias.
"""

import json
from typing import Any

import pytest

from app.models.ats import ATSKeywordMatch
from app.services.ats_analyzer.keyword_matcher import (
    KeywordMatch,
    _parse_keywords,
    _parse_priorities,
    analyze_keywords,
    classify_keyword_priorities,
    extract_job_keyword_priorities,
    extract_job_keywords,
)
from app.services.ats_analyzer.report_store import priorities_from_row
from app.services.ats_analyzer.scoring import (
    NICE_TO_HAVE_WEIGHT,
    compose_ats_score,
    keyword_coverage,
)


class FakeGateway:
    def __init__(self, reply: Any) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    async def generate(
        self,
        _task_type: str,
        _tier: str,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        self.prompts.append(prompt)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply if isinstance(self.reply, str) else json.dumps(self.reply)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.0, 1.0] for _ in texts]


JOB: dict[str, Any] = {"job_title": "Backend Engineer", "raw_text": "texto del aviso"}


# --- lo que devuelve la IA al extraer ------------------------------------------------


def test_keywords_come_with_their_priority_when_the_ai_returns_objects() -> None:
    content = json.dumps(
        {
            "keywords": [
                {"name": "Python", "priority": "required"},
                {"name": "Docker", "priority": "nice"},
                {"name": "Redis", "priority": "NICE_TO_HAVE"},
                {"name": "SQL"},
            ]
        }
    )

    assert _parse_keywords(content, JOB) == ["Docker", "Python", "Redis", "SQL"]
    assert _parse_priorities(content) == {"docker": "nice", "redis": "nice"}


def test_plain_strings_are_still_accepted_and_all_required() -> None:
    content = json.dumps({"keywords": ["Python", "Docker"]})

    assert _parse_keywords(content, JOB) == ["Docker", "Python"]
    assert _parse_priorities(content) == {}


@pytest.mark.parametrize(
    "content",
    ["no es json", json.dumps({"keywords": "Python"}), json.dumps({"otra": 1})],
)
def test_a_reply_with_another_shape_falls_back_without_priorities(content: str) -> None:
    job = {**JOB, "required_skills": ["Python"], "tech_stack": ["Docker"]}

    assert _parse_keywords(content, job) == ["Docker", "Python"]
    assert _parse_priorities(content) == {}


@pytest.mark.parametrize("value", ["Required", "must", "", None, 3, ["nice"]])
def test_only_the_nice_words_make_a_keyword_nice(value: Any) -> None:
    content = json.dumps({"keywords": [{"name": "Python", "priority": value}]})

    assert _parse_priorities(content) == {}


@pytest.mark.asyncio
async def test_the_extraction_returns_the_names_and_the_nice_ones() -> None:
    gateway = FakeGateway(
        {"keywords": [{"name": "Python"}, {"name": "Docker", "priority": "nice"}]}
    )

    keywords, priorities = await extract_job_keyword_priorities(
        JOB,
        gateway,  # type: ignore[arg-type]
    )
    names_only = await extract_job_keywords(JOB, gateway)  # type: ignore[arg-type]

    assert keywords == ["Docker", "Python"]
    assert priorities == {"docker": "nice"}
    assert names_only == keywords


@pytest.mark.asyncio
async def test_the_prompt_explains_what_makes_a_skill_nice_to_have() -> None:
    gateway = FakeGateway({"keywords": []})

    await extract_job_keyword_priorities(JOB, gateway)  # type: ignore[arg-type]

    [prompt] = gateway.prompts
    assert '"priority": "nice"' in prompt
    assert "nice to have" in prompt
    assert "se valora" in prompt
    # Sigue sin pedir idiomas ni títulos como habilidades.
    assert "No incluyas idiomas" in prompt


# --- el análisis -------------------------------------------------------------------


def _cv() -> dict[str, Any]:
    return {"id": "doc", "parsed_data": {"skills": [{"name": "Python"}]}}


@pytest.mark.asyncio
async def test_the_matches_carry_the_priority_of_each_keyword() -> None:
    gateway = FakeGateway(
        {"keywords": [{"name": "Python"}, {"name": "Docker", "priority": "nice"}]}
    )

    result = await analyze_keywords(JOB, _cv(), gateway=gateway)  # type: ignore[arg-type]

    assert [(m.keyword, m.priority) for m in result.matches] == [
        ("Docker", "nice"),
        ("Python", "required"),
    ]
    assert result.matches[1].status == "literal"


@pytest.mark.asyncio
async def test_saved_keywords_use_the_saved_priorities_without_asking_the_ai() -> None:
    gateway = FakeGateway({"keywords": []})

    result = await analyze_keywords(
        JOB,
        _cv(),
        gateway=gateway,  # type: ignore[arg-type]
        keywords=["Python", "Docker"],
        priorities={"docker": "nice"},
    )

    assert {m.keyword: m.priority for m in result.matches} == {
        "Python": "required",
        "Docker": "nice",
    }
    assert gateway.prompts == []


@pytest.mark.asyncio
async def test_saved_keywords_without_priorities_are_all_required() -> None:
    gateway = FakeGateway({"keywords": []})

    result = await analyze_keywords(
        JOB,
        _cv(),
        gateway=gateway,  # type: ignore[arg-type]
        keywords=["Python", "Docker"],
    )

    assert {m.priority for m in result.matches} == {"required"}
    assert gateway.prompts == []


# --- clasificar las de un reporte viejo ----------------------------------------------


@pytest.mark.asyncio
async def test_a_classification_returns_only_known_nice_words() -> None:
    gateway = FakeGateway({"nice": ["Docker", "docker ", "No estaba en la lista", 7]})

    priorities = await classify_keyword_priorities(
        JOB,
        ["Python", "Docker"],
        gateway,  # type: ignore[arg-type]
    )

    assert priorities == {"docker": "nice"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reply",
    [RuntimeError("la IA no respondió"), "no es json", {"nice": "Docker"}, [1, 2], {}],
)
async def test_a_failed_classification_leaves_everything_required(reply: Any) -> None:
    gateway = FakeGateway(reply)

    priorities = await classify_keyword_priorities(
        JOB,
        ["Python", "Docker"],
        gateway,  # type: ignore[arg-type]
    )

    assert priorities == {}


@pytest.mark.asyncio
async def test_there_is_nothing_to_classify_without_keywords() -> None:
    gateway = FakeGateway({"nice": ["Docker"]})

    assert await classify_keyword_priorities(JOB, [], gateway) == {}  # type: ignore[arg-type]
    assert gateway.prompts == []


# --- el reporte guardado -----------------------------------------------------------


def test_priorities_are_read_from_a_report_that_has_them() -> None:
    row = {
        "keyword_matches": [
            {"keyword": "Python", "status": "literal", "priority": "required"},
            {"keyword": "Docker", "status": "missing", "priority": "nice"},
            {"keyword": "Git", "status": "missing"},
        ]
    }

    assert priorities_from_row(row) == {
        "python": "required",
        "docker": "nice",
        "git": "required",
    }


@pytest.mark.parametrize(
    "row",
    [
        None,
        {},
        {"keyword_matches": "texto"},
        {"keyword_matches": []},
        {"keyword_matches": [{"keyword": "Python", "status": "literal"}]},
    ],
)
def test_a_report_from_before_the_priority_has_none(row: Any) -> None:
    assert priorities_from_row(row) is None


def test_a_saved_match_without_priority_reads_as_required() -> None:
    match = ATSKeywordMatch.model_validate({"keyword": "Python", "status": "literal"})

    assert match.priority == "required"


# --- el puntaje ---------------------------------------------------------------------


def _match(status: str, priority: str = "required") -> ATSKeywordMatch:
    return ATSKeywordMatch(keyword=status + priority, status=status, priority=priority)  # type: ignore[arg-type]


def test_a_nice_to_have_keyword_weighs_half() -> None:
    assert NICE_TO_HAVE_WEIGHT == 0.5
    # Una obligatoria presente y una deseable ausente: 1 / 1,5.
    assert keyword_coverage(
        [_match("literal"), _match("missing", "nice")]
    ) == pytest.approx(1 / 1.5)
    # Una obligatoria ausente y una deseable presente: 0,5 / 1,5.
    assert keyword_coverage(
        [_match("missing"), _match("literal", "nice")]
    ) == pytest.approx(0.5 / 1.5)


def test_without_nice_keywords_the_coverage_is_the_same_as_before() -> None:
    matches = [
        _match("literal"),
        _match("semantic"),
        _match("missing"),
        _match("missing"),
    ]

    assert keyword_coverage(matches) == pytest.approx(0.375)
    assert compose_ats_score(matches) == 38


def test_matches_without_a_priority_attribute_count_as_required() -> None:
    plain = [KeywordMatch("a", "literal"), KeywordMatch("b", "missing")]

    assert keyword_coverage(plain) == 0.5


def test_a_missing_nice_word_costs_less_than_a_missing_required_one() -> None:
    lost_required = [_match("literal"), _match("missing")]
    lost_nice = [_match("literal"), _match("missing", "nice")]

    assert compose_ats_score(lost_nice) > compose_ats_score(lost_required)


def test_a_present_nice_word_adds_less_than_a_present_required_one() -> None:
    won_required = [_match("missing"), _match("literal")]
    won_nice = [_match("missing"), _match("literal", "nice")]

    assert compose_ats_score(won_nice) < compose_ats_score(won_required)
