import re
import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FormatIssue:
    code: str
    message: str
    penalty: int


# Palabras de los títulos de sección que un ATS reconoce. Un título las lleva enteras:
# «Experiencia profesional» y «Habilidades y competencias» son habituales.
STANDARD_HEADERS = {
    "experience",
    "experiencia",
    "education",
    "educacion",
    "skills",
    "habilidades",
    "languages",
    "idiomas",
    "certifications",
    "certificaciones",
}

_HEADER_WORD = re.compile(r"[a-z]+")


def _normalize_header(header: str) -> str:
    """Sin mayúsculas, acentos ni dos puntos finales: «Educación:» es «educacion»."""
    decomposed = unicodedata.normalize("NFKD", header.strip().casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(plain.removesuffix(":").split())


def _is_usual_header(header: str) -> bool:
    return any(
        word in STANDARD_HEADERS
        for word in _HEADER_WORD.findall(_normalize_header(header))
    )


def format_was_evaluated(primary_cv: dict[str, Any]) -> bool:
    """¿La lectura del CV dejó sus banderas de formato?

    Los CV leídos antes de que existiera esa lectura no las tienen, y tampoco los que
    fallaron al analizar el diseño del PDF: de esos no se sabe nada, y decir «sin
    problemas» sería afirmar algo que no se miró.
    """
    parsed_data = primary_cv.get("parsed_data")
    return isinstance(parsed_data, dict) and isinstance(
        parsed_data.get("format_flags"), dict
    )


def check_cv_format(primary_cv: dict[str, Any]) -> list[FormatIssue]:
    parsed_data = primary_cv.get("parsed_data")
    if not isinstance(parsed_data, dict):
        return [FormatIssue("NO_PARSED_DATA", "El CV no tiene datos parseados.", 20)]

    flags = parsed_data.get("format_flags") or {}
    issues: list[FormatIssue] = []
    if isinstance(flags, dict):
        if flags.get("has_tables"):
            issues.append(FormatIssue("TABLES", "El CV contiene tablas.", 10))
        if flags.get("multi_column"):
            issues.append(
                FormatIssue("MULTI_COLUMN", "El CV usa múltiples columnas.", 10)
            )
        if flags.get("has_images"):
            issues.append(FormatIssue("IMAGES", "El CV contiene imágenes.", 10))

        # Se resta solo si ningún título es de los habituales: el ATS no encontraría las
        # secciones. Uno raro entre los habituales no cuesta nada, y el lector del PDF a
        # veces toma por título un nombre de empresa en mayúsculas (Decisión 34).
        headers = flags.get("headers") or []
        if (
            isinstance(headers, list)
            and headers
            and not any(_is_usual_header(str(header)) for header in headers)
        ):
            issues.append(
                FormatIssue(
                    "NON_STANDARD_HEADERS",
                    "Ningún título de sección del CV es de los habituales.",
                    5,
                )
            )

    return issues
