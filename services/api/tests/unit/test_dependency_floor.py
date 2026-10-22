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
        # multidict 6.9.1 corrige una fuga de referencias en la unión y la resta de las
        # vistas de items (alerta de Dependabot 82); la pide yarl, no el código propio.
        ("multidict", "6.9.1"),
        # certifi 2026.10.19 saca las raíces de emSign cuyas claves intermedias quedaron
        # comprometidas (GHSA-6q48-6c7w-9gw2). Es el almacén de certificados de todo el
        # HTTPS de salida (httpx, requests, sentry-sdk); no lo pide el código propio.
        ("certifi", "2026.10.19"),
        # Pillow 13.0.0 corrige siete avisos al decodificar imágenes (CVE-2026-112397,
        # 112400, 112403, 112404, 112895, 112896 y 112897). Lo pide pdfplumber; el
        # código propio no lo importa.
        ("pillow", "13.0.0"),
    ],
)
def test_security_sensitive_dependencies_keep_their_minimum_version(
    package: str, minimum: str
) -> None:
    assert Version(version(package)) >= Version(minimum)
