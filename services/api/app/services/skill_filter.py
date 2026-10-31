"""Qué cuenta como habilidad de un puesto: su nombre, no sus datos ni sus tareas.

La IA que extrae las keywords recibía la orden de incluir «seniority, idiomas y
títulos», y el reporte pedía «Junior», «Full time», «Buenos Aires» o el título del
puesto como si fueran habilidades que el CV puede tener o no. Esas palabras no se
buscan en un CV: bajan el puntaje de quien sí cumple (Decisión 35). Acá se descartan,
tanto las que devuelve la IA como las que un reporte viejo dejó guardadas.

El pedido a la IA es la primera defensa (`extract_job_keywords`); esto es la segunda,
y es conservadora: solo descarta lo que seguro no es una habilidad.

Lo usan el ATS y el MatchScore (Decisión 39). Vive fuera de `ats_analyzer` porque el
ATS ya importa del motor de comparación y el motor no puede importar del ATS sin un
ciclo.

- El nivel (junior, senior, «semi senior»…), la modalidad (remoto, híbrido…) y el
  tipo de jornada («full time»), y lo que el puesto guarda como nivel y modalidad:
  es texto libre y suele traer el lugar («Híbrida (presencial en Vicente López)»).
- El título del puesto y el nombre de la empresa, enteros: «Python» sigue valiendo
  aunque esté dentro del título.
- Una ciudad o un país conocido. La lista no es exhaustiva: lo que no figura acá
  queda a cargo del pedido a la IA.
- Una tarea escrita como frase («Escritura de consultas SQL y mantenimiento de base
  de datos»): una habilidad se nombra con pocas palabras.
"""

import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

# Más palabras que esto es una tarea escrita como frase, no el nombre de una habilidad.
MAX_SKILL_WORDS = 5

# Palabras que solo describen el nivel, la modalidad o la jornada. Una keyword hecha
# solo de estas no es una habilidad. «office» no está: «Office» es una herramienta.
_NON_SKILL_WORDS = frozenset(
    {
        # nivel
        "junior",
        "jr",
        "semi",
        "semisenior",
        "senior",
        "sr",
        "ssr",
        "mid",
        "middle",
        "trainee",
        "pasante",
        "pasantia",
        "intern",
        "internship",
        "nivel",
        "level",
        # modalidad
        "remoto",
        "remota",
        "remote",
        "hibrido",
        "hibrida",
        "hybrid",
        "presencial",
        "onsite",
        "teletrabajo",
        "modalidad",
        "home",
        "on",
        "site",
        # jornada
        "full",
        "part",
        "fulltime",
        "parttime",
        "time",
        "tiempo",
        "jornada",
        "completa",
        "completo",
        "parcial",
        "medio",
        # conectores que las acompañan
        "de",
        "la",
        "el",
        "en",
        "y",
    }
)

# «home office» no se descarta por palabras sueltas porque «Office» es una herramienta.
_NON_SKILL_PHRASES = frozenset({"home office", "work from home"})

# Ciudades y países que una oferta menciona. No es una lista completa a propósito.
_PLACES = frozenset(
    {
        "argentina",
        "buenos aires",
        "gran buenos aires",
        "caba",
        "gba",
        "capital federal",
        "ciudad autonoma de buenos aires",
        "cordoba",
        "rosario",
        "mendoza",
        "la plata",
        "mar del plata",
        "tucuman",
        "salta",
        "santa fe",
        "neuquen",
        "bahia blanca",
        "latam",
        "latinoamerica",
        "america latina",
        "mexico",
        "ciudad de mexico",
        "cdmx",
        "colombia",
        "bogota",
        "medellin",
        "chile",
        "santiago de chile",
        "uruguay",
        "montevideo",
        "peru",
        "lima",
        "brasil",
        "brazil",
        "sao paulo",
        "espana",
        "spain",
        "usa",
        "estados unidos",
        "united states",
    }
)

_WORD = re.compile(r"[a-z0-9]+")
_PLACE_SEPARATOR = re.compile(r"[,/|]")


def _words(value: str) -> list[str]:
    """Las palabras de un texto sin acentos ni mayúsculas, sin la puntuación."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _WORD.findall(plain)


def _phrase(value: str) -> str:
    return " ".join(_words(value))


def _is_place(value: str) -> bool:
    parts = [part for part in _PLACE_SEPARATOR.split(value) if _phrase(part)]
    return bool(parts) and all(_phrase(part) in _PLACES for part in parts)


def _field_phrase(job: Mapping[str, Any], field: str) -> str:
    value = job.get(field)
    return _phrase(value) if isinstance(value, str) else ""


def _is_skill(keyword: str, titles: set[str], free_text: list[str]) -> bool:
    words = _words(keyword)
    if not words or len(words) > MAX_SKILL_WORDS:
        return False
    phrase = " ".join(words)
    if phrase in titles or phrase in _NON_SKILL_PHRASES:
        return False
    if all(word in _NON_SKILL_WORDS for word in words):
        return False
    # El nivel y la modalidad del puesto son texto libre y suelen traer el lugar:
    # «Híbrida (presencial en Vicente López, CABA)». Lo que dicen no es una habilidad.
    if any(f" {phrase} " in f" {text} " for text in free_text):
        return False
    return not _is_place(keyword)


def skill_keywords(
    keywords: Iterable[str], job: Mapping[str, Any] | None = None
) -> list[str]:
    """Las keywords que son habilidades, en el mismo orden y sin repetidas."""
    data = job or {}
    titles = {_field_phrase(data, field) for field in ("job_title", "company_name")}
    free_text = [
        text
        for text in (
            _field_phrase(data, field)
            for field in ("required_seniority", "required_modality")
        )
        if text
    ]
    kept: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        text = keyword.strip()
        if text.casefold() in seen or not _is_skill(text, titles - {""}, free_text):
            continue
        seen.add(text.casefold())
        kept.append(text)
    return kept
