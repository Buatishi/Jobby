"""Convierte un documento Markdown en PDF (con diagramas Mermaid e imágenes) usando Edge.

    python docs/tools/build_pdf.py docs/tools/ejemplo/ejemplo.md [-o salida.pdf] [--landscape]

- Los bloques ```mermaid se dibujan con Mermaid (local, versión fijada en tools.lock.json).
- Las imágenes (por ejemplo los SVG que genera render_diagrams.py) se resuelven respecto
  del Markdown.
- Sin -o, el PDF se escribe en `docs/pdf/<nombre>.pdf`.
- --landscape genera las hojas A4 apaisadas (útil para diagramas anchos).
"""

from __future__ import annotations

import argparse
import html
import pathlib
import re
import string
import subprocess
import sys
import tempfile

import markdown

from tooling import HERE, find_edge, load_lock, mermaid_js_path

MERMAID_BLOCK = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)

PAGE = string.Template(
    """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>$title</title>
<base href="$base">
<style>
@page { size: $page_size; margin: 18mm 16mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #111; }
h1 { font-size: 20pt; margin: 0 0 8pt; } h2 { font-size: 15pt; margin: 16pt 0 6pt; }
h3 { font-size: 12pt; margin: 12pt 0 4pt; }
h1, h2, h3 { break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; }
th, td { border: 1px solid #b5b5b5; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #eef2f0; }
code, pre { font-family: Consolas, monospace; font-size: 9pt; }
pre { background: #f4f4f4; padding: 8px; white-space: pre-wrap; }
img, svg { max-width: 100%; height: auto; }
img { max-height: $diagram_height; break-inside: avoid; }
.mermaid { text-align: center; margin: 12px 0; break-inside: avoid; }
.mermaid svg { max-width: 100%; max-height: $diagram_height; }
</style></head><body>
$body
$script
</body></html>
"""
)

MERMAID_SCRIPT = string.Template(
    """<script src="$src"></script>
<script>
mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict" });
mermaid.run({ querySelector: ".mermaid" });
</script>"""
)


def convert_mermaid_blocks(text: str) -> tuple[str, int]:
    """Cambia cada bloque ```mermaid por un <div class="mermaid"> con el texto escapado."""
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f'\n<div class="mermaid">{html.escape(match.group(1).strip())}</div>\n'

    return MERMAID_BLOCK.sub(replace, text), count


def render_html(source: pathlib.Path, landscape: bool = False) -> tuple[str, int]:
    text, diagrams = convert_mermaid_blocks(source.read_text(encoding="utf-8"))
    body = markdown.markdown(
        text, extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"]
    )
    script = ""
    if diagrams:
        mermaid_js = mermaid_js_path(load_lock())
        if not mermaid_js.exists():
            raise SystemExit(
                "Falta Mermaid: ejecutar `python docs/tools/setup_tools.py --install-mermaid`."
            )
        script = MERMAID_SCRIPT.substitute(src=mermaid_js.as_uri())
    page = PAGE.substitute(
        title=html.escape(source.stem),
        page_size="A4 landscape" if landscape else "A4",
        diagram_height="150mm" if landscape else "225mm",
        base=source.parent.resolve().as_uri() + "/",
        body=body,
        script=script,
    )
    return page, diagrams


def build(source: pathlib.Path, output: pathlib.Path, landscape: bool = False) -> None:
    edge = find_edge()
    if edge is None:
        raise SystemExit("No se encontró Microsoft Edge (definir EDGE_PATH).")
    page, _ = render_html(source, landscape)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        html_path = pathlib.Path(tmp) / "documento.html"
        html_path.write_text(page, encoding="utf-8")
        subprocess.run(
            [str(edge), "--headless=new", "--disable-gpu", "--no-first-run",
             "--no-pdf-header-footer", "--allow-file-access-from-files",
             f"--user-data-dir={pathlib.Path(tmp) / 'perfil'}",
             f"--print-to-pdf={output.resolve()}", "--virtual-time-budget=20000",
             html_path.as_uri()],
            check=True, capture_output=True, timeout=180,
        )
    if not output.exists() or output.stat().st_size == 0:
        raise SystemExit("Edge no generó el PDF.")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("markdown", type=pathlib.Path)
    parser.add_argument("-o", "--output", type=pathlib.Path)
    parser.add_argument("--landscape", action="store_true", help="hojas A4 apaisadas")
    args = parser.parse_args()

    output = args.output or HERE.parent / "pdf" / f"{args.markdown.stem}.pdf"
    build(args.markdown, output, args.landscape)
    print(f"PDF generado: {output} ({output.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
