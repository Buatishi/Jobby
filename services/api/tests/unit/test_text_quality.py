"""Heurísticas que separan un dato con información de un relleno (text_quality.py)."""

import pytest

from app.services.text_quality import (
    content_words,
    is_gibberish_word,
    is_linkedin_profile_url,
    is_meaningful_name,
    is_meaningful_text,
)


@pytest.mark.parametrize(
    "text",
    [
        "Chef",
        "Backend Engineer",
        "Contador público",
        "QA Analyst",
        "Analista de datos",
        "IT Manager",
        "Desarrollador Full Stack",
    ],
)
def test_a_real_role_is_meaningful(text: str) -> None:
    assert is_meaningful_text(text)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "asdf",
        "qwerty",
        "aaaa",
        "jajaja",
        "bcdfgh",
        "n/a",
        "N/A",
        "test",
        "Profesional",
        "Persona responsable",
        "Trabajador proactivo",
        "...",
        "12345",
        "chef chef chef",
        "Backend asdfgh",
    ],
)
def test_filler_is_not_a_meaningful_role(text: str) -> None:
    assert not is_meaningful_text(text)


def test_a_bio_needs_enough_distinct_useful_words() -> None:
    informative = (
        "Desarrollador backend con 5 años de experiencia construyendo APIs en "
        "Python para fintech"
    )
    assert is_meaningful_text(informative, min_words=5, min_diversity=0.6)

    generic = "Soy una persona responsable y proactiva con ganas de aprender"
    assert not is_meaningful_text(generic, min_words=5, min_diversity=0.6)

    repeated = "backend backend backend backend backend backend python"
    assert not is_meaningful_text(repeated, min_words=5, min_diversity=0.6)

    too_short = "Ingeniero de software"
    assert not is_meaningful_text(too_short, min_words=5, min_diversity=0.6)


def test_accents_do_not_change_what_counts_as_a_word() -> None:
    assert content_words("Ingeniería de Sistemas") == content_words(
        "ingenieria de sistemas"
    )
    assert content_words("la de y con") == []


@pytest.mark.parametrize("name", ["Python", "C", "R", "Go", "3M", "Node.js", "C++"])
def test_short_real_names_are_meaningful(name: str) -> None:
    assert is_meaningful_name(name)


@pytest.mark.parametrize(
    "name",
    ["", " ", "-", "n/a", "N/A", "test", "asdf", "xxxx", "ninguno", "Aprender", "123"],
)
def test_placeholder_names_are_not_meaningful(name: str) -> None:
    assert not is_meaningful_name(name)


@pytest.mark.parametrize("word", ["sql", "html", "https", "rdbms", "backend", "chef"])
def test_real_words_and_vowelless_acronyms_are_not_gibberish(word: str) -> None:
    assert not is_gibberish_word(word)


@pytest.mark.parametrize("word", ["aaaa", "jajaja", "asdf", "qwert", "bcdfgh"])
def test_noise_is_gibberish(word: str) -> None:
    assert is_gibberish_word(word)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/in/juan-perez",
        "https://linkedin.com/in/juan-perez/",
        "http://ar.linkedin.com/in/juan-perez-123",
        "linkedin.com/in/juan-perez",
        "https://www.linkedin.com/in/juan-perez?utm=1",
    ],
)
def test_a_linkedin_profile_url_is_valid(url: str) -> None:
    assert is_linkedin_profile_url(url)


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "linkedin",
        "https://example.com/in/juan-perez",
        "https://notlinkedin.com/in/juan-perez",
        "https://www.linkedin.com/company/acme",
        "https://www.linkedin.com/in/ab",
        "https://www.linkedin.com/",
        "ftp://www.linkedin.com/in/juan-perez",
    ],
)
def test_other_urls_are_not_a_linkedin_profile(url: str | None) -> None:
    assert not is_linkedin_profile_url(url)
