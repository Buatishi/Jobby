import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class FormatIssue:
    code: str
    message: str
    penalty: int


class _PenalizedIssue(Protocol):
    @property
    def code(self) -> str: ...

    @property
    def penalty(self) -> int: ...


# Lo que no puede tener el CV que arma Jobby (Decisión 26): una sola columna, sin tablas
# ni imágenes. Es lo que `printable-cv-document.tsx` garantiza y que un test del
# frontend vigila: si el documento cambia, esta lista tiene que cambiar con él.
_NOT_IN_THE_DOWNLOADABLE_CV = frozenset({"TABLES", "MULTI_COLUMN", "IMAGES"})


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


def _normalize_header(header: str) -> str:
    """Sin mayúsculas, acentos ni dos puntos finales: «Educación:» es «educacion»."""
    decomposed = unicodedata.normalize("NFKD", header.strip().casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(plain.removesuffix(":").split())


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


def penalty_after_download(issues: Iterable[_PenalizedIssue]) -> int:
    """Puntos de formato que le quedan al CV si se arma con el documento de Jobby.

    Solo se perdonan las tablas, las columnas y las imágenes del archivo original. Los
    títulos no habituales y un CV que no se pudo leer siguen restando: Jobby no sabe
    cómo va a titular la persona sus secciones ni qué decía un archivo ilegible.
    """
    return sum(
        issue.penalty
        for issue in issues
        if issue.code not in _NOT_IN_THE_DOWNLOADABLE_CV
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

        headers = flags.get("headers") or []
        if isinstance(headers, list):
            non_standard = [
                str(header)
                for header in headers
                if _normalize_header(str(header)) not in STANDARD_HEADERS
            ]
            if non_standard:
                issues.append(
                    FormatIssue(
                        "NON_STANDARD_HEADERS",
                        "El CV tiene headers no estándar.",
                        5,
                    )
                )

    return issues
