"""Fechas de un CV y la palabra «actualidad» (Decisión 41).

La IA copia cada fecha como el CV la escribe; el formato lo pone este módulo, sin IA y
sin inventar nada. Una fecha inequívoca se guarda como `AAAA-MM` (o `AAAA` si el CV solo
trae el año): ordena bien como texto, no depende del idioma del CV y la web la muestra
como «Julio 2026». Lo que no es inequívoco (`15/03/2021` puede ser día/mes o mes/día,
«Verano 2020») queda como lo escribió el CV, y lo que no es una fecha se descarta.

Ninguna función levanta una excepción: la IA devuelve nulos, objetos y listas donde se
pidió un texto, y una fecha mal escrita no puede hacer fallar el análisis de un CV.
"""

import re
from typing import Any

from app.services.text_quality import fold

# Un párrafo no es una fecha: «Julio de 2026» mide 13.
MAX_DATE_LENGTH = 40
_MIN_YEAR = 1900
_MAX_YEAR = 2100

_MONTHS = {
    "enero": 1, "ene": 1, "january": 1, "jan": 1,
    "febrero": 2, "feb": 2, "february": 2,
    "marzo": 3, "mar": 3, "march": 3,
    "abril": 4, "abr": 4, "april": 4, "apr": 4,
    "mayo": 5, "may": 5,
    "junio": 6, "jun": 6, "june": 6,
    "julio": 7, "jul": 7, "july": 7,
    "agosto": 8, "ago": 8, "august": 8, "aug": 8,
    "septiembre": 9, "setiembre": 9, "sept": 9, "sep": 9, "september": 9,
    "octubre": 10, "oct": 10, "october": 10,
    "noviembre": 11, "nov": 11, "november": 11,
    "diciembre": 12, "dic": 12, "december": 12, "dec": 12,
}  # fmt: skip

_MONTH_WORDS = "|".join(sorted(_MONTHS, key=len, reverse=True))
_ISO = re.compile(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?")
_MONTH_YEAR = re.compile(r"(\d{1,2})\s*[/.\-]\s*(\d{4})")
_YEAR_MONTH = re.compile(r"(\d{4})\s*/\s*(\d{1,2})")
# «15 de julio de 2026», «Sept. 2019», «Aug, 2018»: el día, si está, no se guarda.
_WORD_MONTH_YEAR = re.compile(
    rf"(?:\d{{1,2}}\s+(?:de\s+)?)?({_MONTH_WORDS})\.?,?\s+(?:(?:de|of)\s+)?(\d{{4}})"
)

# Las palabras con las que un CV dice que algo sigue: «Presente», «Actualidad»,
# «A la fecha», «En curso» (estudios). «Date: 2020» o «Actualizado 2020» no cuentan.
_PRESENT = re.compile(
    r"(?:(?:hasta|a|al|to|until|up to)\s+(?:(?:la|el)\s+)?"
    r"(?:fecha|date|actualidad|presente|present)"
    r"|presente|actual(?:idad|mente)?|hoy|present|current(?:ly)?|now|today|ongoing"
    r"|vigente|en curso|cursando|in progress)\b"
)

_YEAR_RANGE = re.compile(r"(\d{4})\s*-\s*(\d{4})")
_RANGE_SEPARATOR = re.compile(
    r"\s*[–—]\s*|\s+-\s+|\s+(?:a|al|to|until|hasta)\s+", re.IGNORECASE
)
_TRUE = frozenset({"true", "yes", "si", "1", "verdadero"})


def _is_year(value: float) -> bool:
    # Un entero enorme no se pasa por float() (OverflowError); inf y nan no son enteros.
    if isinstance(value, int):
        return _MIN_YEAR <= value <= _MAX_YEAR
    return value.is_integer() and _MIN_YEAR <= value <= _MAX_YEAR


def _scalar(value: Any) -> str:
    """Un texto o un año; todo lo demás (None, listas, objetos, booleanos) es vacío."""
    if isinstance(value, bool):
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, int | float):
        return str(int(value)) if _is_year(value) else ""
    return ""


def _month_number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        number = value
    elif isinstance(value, float):
        number = int(value) if value.is_integer() else 0
    else:
        text = fold(_scalar(value)).rstrip(".")
        number = int(text) if text.isdigit() else _MONTHS.get(text, 0)
    return number if 1 <= number <= 12 else None


def date_text(value: Any) -> str:
    """La fecha como texto: un año o `{year, month}` se arman; lo demás se lee."""
    if isinstance(value, dict):
        year = _scalar(value.get("year"))
        if year.isdigit() and _MIN_YEAR <= int(year) <= _MAX_YEAR:
            month = _month_number(value.get("month"))
            return f"{year}-{month:02d}" if month else year
        for key in ("text", "value", "date"):
            text = _scalar(value.get(key))
            if text:
                return text
        return ""
    return _scalar(value)


def normalize_date(value: Any) -> str:
    """`AAAA-MM` o `AAAA` si la fecha es inequívoca; si no, el texto del CV.

    Lo que no es una fecha (largo de párrafo, un objeto sin año) queda vacío.
    """
    text = date_text(value)
    if not text or len(text) > MAX_DATE_LENGTH:
        return ""

    # Ya viene en ISO (o es un año suelto): se respeta lo que trae, aunque el mes sea 13
    # o el año 1850; no hay con qué corregirlo y no se inventa otro valor.
    if _ISO.fullmatch(text):
        return text

    folded = fold(text).rstrip(".,;")
    month_year = _MONTH_YEAR.fullmatch(folded)
    if month_year:
        month, year = month_year.groups()
        return _year_month(year, month, text)
    year_month = _YEAR_MONTH.fullmatch(folded)
    if year_month:
        year, month = year_month.groups()
        return _year_month(year, month, text)
    word_month = _WORD_MONTH_YEAR.fullmatch(folded)
    if word_month:
        word, year = word_month.groups()
        return _year_month(year, str(_MONTHS[word]), text)
    return text


def _year_month(year: str, month: str, original: str) -> str:
    if _MIN_YEAR <= int(year) <= _MAX_YEAR and 1 <= int(month) <= 12:
        return f"{year}-{int(month):02d}"
    return original


def is_present_marker(value: Any) -> bool:
    """¿El texto dice que sigue vigente («Presente», «Actualidad», «En curso»)?"""
    if not isinstance(value, str):
        return False
    cleaned = " ".join(re.sub(r"[^\w\s]", " ", fold(value)).split())
    return _PRESENT.match(cleaned) is not None


def as_flag(value: Any) -> bool:
    """El booleano que la IA quiso decir: `true`, «sí», `1`; lo demás es no."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value == 1
    if isinstance(value, str):
        return fold(value) in _TRUE
    return False


def first_value(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = item.get(key)
        if value is None or (isinstance(value, str | list | dict) and not value):
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _split_range(text: str) -> tuple[str, str]:
    years = _YEAR_RANGE.fullmatch(text)
    if years:
        return years.group(1), years.group(2)
    parts = _RANGE_SEPARATOR.split(text, maxsplit=1)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return parts[0].strip(), parts[1].strip()
    return text, ""


def read_period(
    item: dict[str, Any],
    start_keys: tuple[str, ...],
    end_keys: tuple[str, ...],
    flag_keys: tuple[str, ...],
) -> tuple[str, str, bool]:
    """Inicio, fin y si sigue vigente, de un trabajo o un estudio.

    - Un fin que dice «Presente» no se guarda como fecha: queda vacío y vigente.
    - Un fin con fecha real gana sobre la bandera de la IA: la fecha sale del CV y la
      bandera es una inferencia.
    - La IA a veces escribe el período entero en el inicio («Julio 2026 - Presente»): si
      no hay fin, se separa.
    """
    start = date_text(first_value(item, start_keys))
    end = date_text(first_value(item, end_keys))
    if start and not end:
        start, end = _split_range(start)

    by_word = is_present_marker(end)
    ended = "" if by_word else normalize_date(end)
    flag = as_flag(first_value(item, flag_keys))
    return normalize_date(start), ended, by_word or (flag and not ended)
