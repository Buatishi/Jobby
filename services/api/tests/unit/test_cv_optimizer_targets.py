"""El optimizador ubica cada experiencia por su id y respalda las keywords que el CV
dice con otras palabras (Decisión 24).

Dos fallas medidas en producción el 2026-11-02 con el CV del autor:

- La IA devolvía el fragmento de una experiencia como un registro («Desarrollador
  Freelance — Python & Salesforce | Pyme | 2026-03 a…») y no como el texto de una
  viñeta, así que la web no encontraba dónde reemplazarlo.
- «Testing» figuraba «sin respaldo» aunque el CV dice «casos de prueba documentados»:
  el respaldo no miraba el español contra el inglés y el puntaje «después» no se movía.
"""

import json
from typing import Any

import pytest

from app.models.ats import ATSKeywordMatch, OptimizedCVSection
from app.services.ats_analyzer.cv_optimizer import (
    _prompt,
    _supported_by_cv,
    attach_targets,
    evidence_texts,
    optimize_cv_sections,
    score_after_optimization,
    verify_sections,
)
from app.services.skill_names import same_skill

CV: dict[str, Any] = {
    "id": "doc-1",
    "parsed_data": {
        "summary": "Desarrollador backend con foco en automatización.",
        "skills": [{"name": "Python"}, {"name": "Pytest"}],
        "experiences": [
            {
                "title": "Desarrollador Freelance — Python & Salesforce",
                "company": "Pyme",
                "started_at": "2026-03",
                "ended_at": "2026-05",
                "description": "",
                "achievements": [
                    "Pipeline end-to-end de automatización de facturas",
                    "Manejo de errores, logging y casos de prueba documentados",
                ],
            },
            {
                "title": "Operador y Analista Digital",
                "company": "Independiente",
                "started_at": "2024-01",
                "ended_at": "2024-10",
                "description": "",
                "achievements": [
                    "Análisis de mercado e identificación de oportunidades"
                ],
            },
        ],
        "educations": [{"field_of_study": "Técnico Informático"}],
        "certifications": [{"name": "Excel Basics for Data Analysis"}],
    },
}


def _section(**fields: Any) -> OptimizedCVSection:
    base: dict[str, Any] = {
        "section_name": "experiences",
        "original_excerpt": "",
        "rewritten_text": "",
        "added_keywords": [],
        "rationale": "",
    }
    return OptimizedCVSection(**{**base, **fields})


# --- el pedido a la IA ----------------------------------------------------------


def test_each_experience_goes_to_the_ai_with_an_id() -> None:
    prompt = _prompt(CV, {"job_title": "Dev"}, [])

    cv_part = prompt.split("CV_SECTIONS:\n", 1)[1]
    experiences = json.loads(cv_part)["experiences"]
    assert [item["id"] for item in experiences] == ["exp-1", "exp-2"]


def test_the_prompt_asks_for_the_target_and_bullets_without_the_header() -> None:
    prompt = _prompt(CV, {"job_title": "Dev"}, [])

    assert '"target_id":"string"' in prompt
    assert "target_id es el id" in prompt
    assert "sin cargo, empresa ni fechas" in prompt


# --- a qué experiencia se refiere cada sección ---------------------------------------


def test_the_id_the_ai_returns_picks_the_experience() -> None:
    [section] = attach_targets([_section(target_id="exp-2")], CV)

    assert section.target_id == "exp-2"
    assert section.target_company == "Independiente"
    assert section.target_title == "Operador y Analista Digital"


def test_a_record_style_excerpt_without_id_is_recognized_by_title_and_company() -> None:
    # Como lo devolvió la IA en el CV real del autor.
    excerpt = (
        "Desarrollador Freelance — Python & Salesforce | Pyme | 2026-03 a 2026-05 | "
        "Pipeline end-to-end de automatización de facturas"
    )

    [section] = attach_targets([_section(original_excerpt=excerpt)], CV)

    assert section.target_id == "exp-1"
    assert section.target_company == "Pyme"
    assert section.target_title == "Desarrollador Freelance — Python & Salesforce"


def test_an_id_that_does_not_exist_falls_back_to_the_excerpt() -> None:
    [section] = attach_targets(
        [
            _section(
                target_id="exp-9",
                original_excerpt="Operador y Analista Digital | Independiente | 2024",
            )
        ],
        CV,
    )

    assert section.target_id == "exp-2"


def test_the_company_breaks_a_tie_between_experiences_with_the_same_title() -> None:
    cv = {
        "id": "doc-2",
        "parsed_data": {
            "experiences": [
                {"title": "Analista", "company": "Andina", "achievements": ["a"]},
                {"title": "Analista", "company": "Boreal", "achievements": ["b"]},
            ]
        },
    }

    [section] = attach_targets(
        [_section(original_excerpt="Analista | Boreal | 2025")], cv
    )

    assert section.target_company == "Boreal"


def test_an_ambiguous_or_unknown_experience_is_not_guessed() -> None:
    cv = {
        "id": "doc-2",
        "parsed_data": {
            "experiences": [
                {"title": "Analista", "company": "Andina", "achievements": ["a"]},
                {"title": "Analista", "company": "Boreal", "achievements": ["b"]},
            ]
        },
    }

    ambiguous = attach_targets([_section(original_excerpt="Analista | 2025")], cv)
    unknown = attach_targets([_section(original_excerpt="Chef | Cocina")], CV)

    assert ambiguous[0].target_id == ""
    assert unknown[0].target_id == ""


def test_other_sections_are_left_alone() -> None:
    section = _section(section_name="summary", original_excerpt="Desarrollador backend")

    [result] = attach_targets([section], CV)

    assert result == section


def test_a_cv_without_parsed_experiences_resolves_nothing() -> None:
    [section] = attach_targets(
        [_section(target_id="exp-1")], {"id": "x", "parsed_data": {}}
    )

    assert section.target_id == "exp-1"
    assert section.target_company == ""


# --- el respaldo por otras palabras -----------------------------------------------


@pytest.mark.parametrize(
    ("keyword", "evidence"),
    [
        ("Testing", ["Manejo de errores, logging y casos de prueba documentados"]),
        ("Software design", ["Diseño de software orientado a servicios"]),
        ("Software architecture", ["Arquitectura de software"]),
        ("Software maintenance", ["Mantenimiento de software"]),
        ("Business analysis", ["Análisis de negocio y requerimientos"]),
        ("Object-oriented programming", ["Programación orientada a objetos"]),
        ("Observability", ["Observabilidad de servicios"]),
        ("Code quality", ["Calidad del código"]),
    ],
)
def test_a_keyword_the_cv_says_in_other_words_is_backed(
    keyword: str, evidence: list[str]
) -> None:
    assert _supported_by_cv(keyword, evidence) is True


@pytest.mark.parametrize(
    ("keyword", "evidence"),
    [
        ("LangChain", ["Pipeline end-to-end de automatización"]),
        ("Software design", ["Diseño de interiores"]),
        ("Testing", ["Pipeline end-to-end de automatización"]),
        ("Go", ["Go to market con equipos comerciales"]),
        ("R", ["Experiencia con R y Python"]),
        ("", ["texto"]),
    ],
)
def test_a_keyword_the_cv_does_not_say_is_not_backed(
    keyword: str, evidence: list[str]
) -> None:
    assert _supported_by_cv(keyword, evidence) is False


def test_all_the_words_of_the_keyword_must_be_in_the_same_text() -> None:
    # «software» y «diseño» en textos distintos no respaldan «software design».
    assert (
        _supported_by_cv("Software design", ["Software de gestión", "Diseño gráfico"])
        is False
    )


def test_the_new_generic_words_equate_the_same_name_in_both_languages() -> None:
    assert same_skill("Mantenimiento de software", "Software maintenance")
    assert same_skill("Análisis de negocio", "Business analysis")
    assert same_skill("Calidad de código", "Code quality")
    assert same_skill("Observabilidad", "Observability")
    # Lo parecido pero distinto sigue sin igualarse.
    assert not same_skill("Calidad de aire", "Code quality")
    assert not same_skill("Software maintenance", "Software design")


def test_the_evidence_is_the_clean_text_of_the_cv_without_keys_or_ids() -> None:
    texts = evidence_texts(CV)

    assert "Manejo de errores, logging y casos de prueba documentados" in texts
    assert "Pytest" in texts
    assert "Excel Basics for Data Analysis" in texts
    assert all("exp-" not in text and "{" not in text for text in texts)


# --- la verificación y el puntaje «después» ---------------------------------------


MATCHES = [
    ATSKeywordMatch(keyword="Python", status="literal", matched_text="Python"),
    ATSKeywordMatch(keyword="Testing", status="missing"),
    ATSKeywordMatch(keyword="LangChain", status="missing"),
    ATSKeywordMatch(keyword="Software design", status="missing"),
]


def _verified(text: str, added: list[str]) -> OptimizedCVSection:
    [section] = verify_sections(
        [_section(section_name="summary", rewritten_text=text, added_keywords=added)],
        MATCHES,
        json.dumps(CV["parsed_data"]),
        evidence_texts(CV),
    )
    return section


def test_a_missing_keyword_the_cv_backs_is_verified_and_counted() -> None:
    section = _verified("Backend con testing y LangChain", ["Testing", "LangChain"])

    assert section.added_keywords == ["Testing"]
    assert section.backed_keywords == ["Testing"]
    assert section.unverified_keywords == ["LangChain"]


def test_a_backed_keyword_the_ai_did_not_declare_still_counts() -> None:
    section = _verified("Backend con testing automatizado", [])

    assert section.backed_keywords == ["Testing"]
    assert section.unverified_keywords == []


def test_a_backed_keyword_the_text_does_not_write_does_not_count() -> None:
    section = _verified("Backend con foco en automatización", ["Testing"])

    assert section.backed_keywords == []
    assert section.added_keywords == []


def test_the_score_after_moves_only_with_what_the_cv_backs() -> None:
    backed = _verified("Backend con testing y LangChain", ["Testing", "LangChain"])
    nothing = _verified("Backend con LangChain", ["LangChain"])

    # Python y Testing de cuatro: 2 de 4 contra 1 de 4.
    assert score_after_optimization([backed], MATCHES, []) == 50
    assert score_after_optimization([nothing], MATCHES, []) == 25


def test_a_section_the_ai_declared_but_nobody_backed_does_not_move_the_score() -> None:
    raw = _section(
        section_name="summary",
        rewritten_text="testing y LangChain",
        added_keywords=["Testing", "LangChain"],
    )

    # Sin verificar (`backed_keywords` vacío): no hay respaldo, no cuenta.
    assert score_after_optimization([raw], MATCHES, []) == 25


# --- de punta a punta -------------------------------------------------------------


class _Gateway:
    def __init__(self, sections: list[dict[str, Any]]) -> None:
        self.sections = sections

    async def generate(self, *_args: Any, **_kwargs: Any) -> str:
        return json.dumps({"sections": self.sections})


@pytest.mark.asyncio
async def test_the_optimizer_returns_targets_and_backed_keywords() -> None:
    gateway = _Gateway(
        [
            {
                "section_name": "experiences",
                "target_id": "exp-1",
                "original_excerpt": "Manejo de errores y casos de prueba documentados",
                "rewritten_text": "Testing automatizado con pytest y manejo de errores",
                "added_keywords": ["Testing"],
                "rationale": "Usa el vocabulario del puesto.",
            },
            {
                "section_name": "experiences",
                "original_excerpt": "Operador y Analista Digital | Independiente",
                "rewritten_text": "Analisis de mercado",
                "added_keywords": [],
                "rationale": "",
            },
        ]
    )

    sections = await optimize_cv_sections(
        CV,
        {"job_title": "Dev"},
        MATCHES,
        "free",
        gateway=gateway,  # type: ignore[arg-type]
    )

    assert [section.target_company for section in sections] == ["Pyme", "Independiente"]
    assert sections[0].backed_keywords == ["Testing"]
    assert score_after_optimization(sections, MATCHES, []) == 50
