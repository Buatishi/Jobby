"""Versiones mínimas por seguridad: si el lock vuelve atrás, este test lo avisa."""

from importlib.metadata import version

import pytest
from packaging.version import Version


@pytest.mark.parametrize(
    ("package", "minimum"),
    [
        # PyJWT valida el token de cada sesión; las 2.13 y anteriores tienen avisos de
        # seguridad (CVE-2026-102266 a 102273).
        ("PyJWT", "2.15"),
        # urllib3 2.8 corrige memoria sin límite al leer respuestas por trozos.
        ("urllib3", "2.8"),
    ],
)
def test_security_sensitive_dependencies_keep_their_minimum_version(
    package: str, minimum: str
) -> None:
    assert Version(version(package)) >= Version(minimum)
