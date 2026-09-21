"""Renderiza los diagramas PlantUML (.puml) a SVG o PNG junto a su archivo fuente.

    python docs/tools/render_diagrams.py [rutas...] [--format svg|png]

Sin rutas procesa todo `docs/`. Usa el layout Smetana (no requiere Graphviz): incluir
`!pragma layout smetana` en cada diagrama.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

from tooling import HERE, find_java, find_plantuml_jar

DEFAULT_ROOT = HERE.parent


def collect(paths: list[str]) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for raw in paths or [str(DEFAULT_ROOT)]:
        path = pathlib.Path(raw)
        files.extend(sorted(path.rglob("*.puml")) if path.is_dir() else [path])
    return files


def render(java: pathlib.Path, jar: pathlib.Path, source: pathlib.Path, fmt: str) -> str | None:
    """Devuelve un mensaje de error o None si se generó bien."""
    done = subprocess.run(
        [str(java), "-Djava.awt.headless=true", "-jar", str(jar),
         f"-t{fmt}", "-charset", "UTF-8", str(source)],
        capture_output=True, text=True, timeout=120,
    )
    output = source.with_suffix(f".{fmt}")
    if done.returncode != 0 or not output.exists():
        return (done.stderr or done.stdout or "PlantUML falló").strip()
    if fmt == "svg" and "Syntax Error" in output.read_text(encoding="utf-8", errors="ignore"):
        return "PlantUML generó una imagen de error de sintaxis"
    return None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--format", choices=("svg", "png"), default="svg")
    args = parser.parse_args()

    java, jar = find_java(), find_plantuml_jar()
    if java is None or jar is None:
        print("Falta Java o plantuml.jar: ejecutar `python docs/tools/setup_tools.py --check`.")
        return 2

    files = collect(args.paths)
    failures = 0
    for source in files:
        error = render(java, jar, source, args.format)
        if error:
            failures += 1
            print(f"ERROR  {source}: {error}")
        else:
            print(f"ok     {source} -> {source.with_suffix('.' + args.format).name}")
    print(f"\n{len(files) - failures}/{len(files)} diagramas generados.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
