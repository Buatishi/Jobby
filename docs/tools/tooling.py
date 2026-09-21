"""Rutas y verificaciones compartidas por las herramientas de documentación."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
LOCK_FILE = HERE / "tools.lock.json"
TOOLS_HOME = pathlib.Path(
    os.environ.get("JOBBY_TOOLS_HOME", pathlib.Path.home() / "tools")
)


def load_lock() -> dict:
    return json.loads(LOCK_FILE.read_text(encoding="utf-8"))


def sha256_of(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_java() -> pathlib.Path | None:
    explicit = os.environ.get("JAVA")
    if explicit and pathlib.Path(explicit).exists():
        return pathlib.Path(explicit)
    on_path = shutil.which("java")
    if on_path:
        return pathlib.Path(on_path)
    for pattern in ("jre*/*/bin/java.exe", "jre*/bin/java.exe", "jre*/*/bin/java"):
        for candidate in sorted(TOOLS_HOME.glob(pattern)):
            return candidate
    return None


def find_plantuml_jar() -> pathlib.Path | None:
    explicit = os.environ.get("PLANTUML_JAR")
    path = pathlib.Path(explicit) if explicit else TOOLS_HOME / "plantuml.jar"
    return path if path.exists() else None


def mermaid_js_path(lock: dict) -> pathlib.Path:
    return TOOLS_HOME / "mermaid" / lock["mermaid"]["version"] / "mermaid.min.js"


def find_edge() -> pathlib.Path | None:
    explicit = os.environ.get("EDGE_PATH")
    candidates = [pathlib.Path(explicit)] if explicit else []
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        if base:
            candidates.append(
                pathlib.Path(base) / "Microsoft/Edge/Application/msedge.exe"
            )
    on_path = shutil.which("msedge")
    if on_path:
        candidates.append(pathlib.Path(on_path))
    return next((path for path in candidates if path.exists()), None)
