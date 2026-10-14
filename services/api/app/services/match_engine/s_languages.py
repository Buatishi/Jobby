import re
from typing import Any

from app.services.match_engine.common import clamp, normalize_text
from app.services.text_quality import STOPWORDS, fold

LANGUAGE_LEVEL = {
    "basic": 1,
    "beginner": 1,
    "intermediate": 2,
    "professional": 3,
    "advanced": 3,
    "native": 4,
    "bilingual": 4,
}

# Idioma (sin acentos y en minúscula) -> clave canónica. La IA devuelve el puesto en
# el idioma del aviso y la persona carga el perfil en español: «English» y «Inglés»
# tienen que ser el mismo idioma.
_LANGUAGE_NAMES = {
    "ingles": "english",
    "english": "english",
    "espanol": "spanish",
    "spanish": "spanish",
    "portugues": "portuguese",
    "portuguese": "portuguese",
    "frances": "french",
    "french": "french",
    "aleman": "german",
    "german": "german",
    "italiano": "italian",
    "italian": "italian",
}

# Palabra de nivel (sin acentos) -> clave de LANGUAGE_LEVEL. Los códigos son del MCER:
# A1/A2 básico, B1/B2 intermedio, C1 avanzado y C2 dominio, que equivale a nativo.
_LEVEL_WORDS = {
    "basico": "basic",
    "basica": "basic",
    "basic": "basic",
    "beginner": "beginner",
    "a1": "basic",
    "a2": "basic",
    "intermedio": "intermediate",
    "intermedia": "intermediate",
    "intermediate": "intermediate",
    "b1": "intermediate",
    "b2": "intermediate",
    "avanzado": "advanced",
    "avanzada": "advanced",
    "advanced": "advanced",
    "c1": "advanced",
    "nativo": "native",
    "nativa": "native",
    "native": "native",
    "c2": "native",
    "bilingue": "bilingual",
    "bilingual": "bilingual",
}

DEFAULT_LEVEL = "intermediate"

_TOKEN = re.compile(r"[a-z0-9]+")
_NOISE = STOPWORDS | {"nivel", "level"}


def _tokens(text: Any) -> list[str]:
    return _TOKEN.findall(fold(str(text or "")))


def _language_keys(text: Any) -> list[str]:
    """Los idiomas que nombra un texto como «Inglés intermedio (B1/B2)».

    Devuelve la clave canónica de cada idioma conocido. Si el texto nombra uno que
    no está en la tabla («Chino mandarín»), usa el texto sin palabras de nivel, así
    «Chino intermedio» del puesto sigue coincidiendo con «Chino» del perfil.
    """
    tokens = _tokens(text)
    known = list(
        dict.fromkeys(
            _LANGUAGE_NAMES[token] for token in tokens if token in _LANGUAGE_NAMES
        )
    )
    if known or not tokens:
        return known
    rest = [t for t in tokens if t not in _LEVEL_WORDS and t not in _NOISE]
    return [" ".join(rest) or " ".join(tokens)]


def _level_in(text: Any) -> str | None:
    """Clave de LANGUAGE_LEVEL del nivel más bajo que nombra el texto, o None.

    «B1/B2» o «intermedio/avanzado» son un rango: lo que pide el puesto es su piso.
    """
    keys = [_LEVEL_WORDS[t] for t in _tokens(text) if t in _LEVEL_WORDS]
    return min(keys, key=LANGUAGE_LEVEL.__getitem__) if keys else None


def _requirements(item: Any) -> list[dict[str, str]]:
    """Un idioma pedido, como texto o como {"name", "level"}, en uno o más requisitos.

    Un mismo texto puede nombrar varios idiomas («Inglés y portugués»): cada uno
    queda como requisito, con el nivel que nombra el texto.
    """
    if isinstance(item, dict):
        name, explicit = item.get("name"), normalize_text(item.get("level"))
    else:
        name, explicit = item, ""
    # Manda el nivel explícito del dict; si no, el del nombre; si no, intermedio.
    level = (
        (explicit if explicit in LANGUAGE_LEVEL else _level_in(explicit))
        or _level_in(name)
        or DEFAULT_LEVEL
    )
    return [{"name": key, "level": level} for key in _language_keys(name)]


def _required_languages(job: dict[str, Any]) -> list[dict[str, str]]:
    required = job.get("required_languages")
    if isinstance(required, dict):
        required = required.get("languages", required.get("required"))
    if not isinstance(required, list):
        return []
    return [requirement for item in required for requirement in _requirements(item)]


def _profile_levels(profile_languages: list[dict[str, Any]]) -> dict[str, int]:
    """Nivel más alto que tiene la persona en cada idioma, por clave canónica.

    «Inglés» y «English» ahora son el mismo idioma: si el perfil trae los dos, vale el
    mejor nivel y no el último que se haya leído.
    """
    levels: dict[str, int] = {}
    for language in profile_languages:
        level = LANGUAGE_LEVEL.get(
            normalize_text(language.get("proficiency") or language.get("level")),
            LANGUAGE_LEVEL[DEFAULT_LEVEL],
        )
        for key in _language_keys(language.get("name")):
            levels[key] = max(level, levels.get(key, 0))
    return levels


def compute_languages_score(
    profile_languages: list[dict[str, Any]],
    job: dict[str, Any],
) -> float:
    required = _required_languages(job)
    if not required:
        return 0.85

    profile_levels = _profile_levels(profile_languages)
    scores: list[float] = []
    for language in required:
        user_level = profile_levels.get(language["name"])
        if user_level is None:
            scores.append(0.0)
            continue

        required_level = LANGUAGE_LEVEL.get(
            language["level"], LANGUAGE_LEVEL[DEFAULT_LEVEL]
        )
        if user_level >= required_level:
            scores.append(1.0)
        else:
            scores.append(clamp(1.0 - (required_level - user_level) * 0.25))

    return clamp(sum(scores) / len(required))
