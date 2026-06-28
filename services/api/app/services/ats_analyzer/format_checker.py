from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FormatIssue:
    code: str
    message: str
    penalty: int


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
                if str(header).strip().lower() not in STANDARD_HEADERS
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
