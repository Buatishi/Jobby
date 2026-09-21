"""Comprueba las herramientas de documentación e instala Mermaid con verificación.

    python docs/tools/setup_tools.py --check
    python docs/tools/setup_tools.py --install-mermaid

Mermaid se descarga del registro oficial de npm y solo se instala si el hash SHA-512 del
paquete coincide con el de `tools.lock.json` y el archivo extraído coincide con su SHA-256.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import sys
import tarfile
import urllib.request

from tooling import (
    TOOLS_HOME,
    find_edge,
    find_java,
    find_plantuml_jar,
    load_lock,
    mermaid_js_path,
    sha256_of,
)


def check() -> int:
    lock = load_lock()
    missing = 0

    java = find_java()
    print(f"java       : {java or 'NO ENCONTRADO (instalar Temurin JRE 21)'}")
    missing += java is None

    jar = find_plantuml_jar()
    if jar is None:
        print("plantuml   : NO ENCONTRADO (descargar plantuml.jar del release oficial)")
        missing += 1
    else:
        good = sha256_of(jar) == lock["plantuml"]["sha256"]
        print(f"plantuml   : {jar} [{'hash OK' if good else 'HASH DISTINTO'}]")
        missing += not good

    mermaid = mermaid_js_path(lock)
    if not mermaid.exists():
        print(f"mermaid    : NO INSTALADO (python docs/tools/setup_tools.py --install-mermaid)")
        missing += 1
    else:
        good = sha256_of(mermaid) == lock["mermaid"]["sha256"]
        print(f"mermaid    : {mermaid} [{'hash OK' if good else 'HASH DISTINTO'}]")
        missing += not good

    edge = find_edge()
    print(f"edge (pdf) : {edge or 'NO ENCONTRADO'}")
    missing += edge is None

    print(f"\nCarpeta de herramientas: {TOOLS_HOME}")
    print("Todo listo." if not missing else f"Faltan o difieren {missing} elemento(s).")
    return 1 if missing else 0


def install_mermaid() -> int:
    lock = load_lock()["mermaid"]
    version = lock["version"]
    url = f"https://registry.npmjs.org/mermaid/-/mermaid-{version}.tgz"
    print(f"Descargando {url} ...")
    data = urllib.request.urlopen(url, timeout=180).read()  # noqa: S310 - URL fija y https

    integrity = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()
    if integrity != lock["npm_integrity"]:
        print("ERROR: el hash SHA-512 del paquete no coincide con tools.lock.json.")
        return 1

    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        member = archive.extractfile(lock["file"])
        if member is None:
            print(f"ERROR: {lock['file']} no está en el paquete.")
            return 1
        content = member.read()

    sha256 = hashlib.sha256(content).hexdigest()
    if lock.get("sha256") and sha256 != lock["sha256"]:
        print("ERROR: el SHA-256 de mermaid.min.js no coincide con tools.lock.json.")
        return 1

    destination = mermaid_js_path(load_lock())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    print(f"Instalado {destination} ({len(content) / 1e6:.1f} MB, sha256 {sha256})")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verifica las herramientas")
    parser.add_argument("--install-mermaid", action="store_true")
    args = parser.parse_args()
    if args.install_mermaid:
        return install_mermaid()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
