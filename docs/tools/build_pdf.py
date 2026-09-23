"""Convierte un Markdown en PDF (con diagramas Mermaid e imágenes) usando Edge o Chrome.

    python docs/tools/build_pdf.py docs/tools/ejemplo/ejemplo.md [-o salida.pdf] [--landscape]
    python docs/tools/build_pdf.py docs/diagramas/x.svg --paper A3 [--title "Título"]

- Los bloques ```mermaid se dibujan con Mermaid (local, versión fijada en tools.lock.json).
- Las imágenes (por ejemplo los SVG que genera render_diagrams.py) se resuelven respecto
  del Markdown.
- Un .svg como entrada genera un PDF con ese único diagrama y su título.
- Los enlaces a archivos del repositorio quedan como texto; los enlaces web se conservan.
- Sin -o, el PDF se escribe en `docs/pdf/<nombre>.pdf`.
- --landscape genera las hojas apaisadas (útil para diagramas anchos).
- --paper A3 usa hojas A3: los diagramas grandes se imprimen con el texto legible.
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

from tooling import HERE, find_browsers, load_lock, mermaid_js_path

MERMAID_BLOCK = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)
LINK = re.compile(r'<a href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
EXTERNAL_HREF = re.compile(r"^(https?:|mailto:|#)")

# Alto máximo de cada diagrama según la hoja: deja lugar al título dentro del margen.
DIAGRAM_HEIGHT = {
    ("A4", False): "225mm",
    ("A4", True): "150mm",
    ("A3", False): "330mm",
    ("A3", True): "225mm",
}

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


def unlink_relative_links(body: str) -> str:
    """Deja como texto los enlaces a archivos del repositorio.

    Edge los convertiría en rutas absolutas del equipo (`C:/Users/...`): no abren para quien
    recibe el PDF y exponen la ruta local. Los enlaces web y las anclas se conservan.
    """
    return LINK.sub(
        lambda m: m.group(0) if EXTERNAL_HREF.match(m.group(1)) else m.group(2), body
    )


def svg_as_markdown(source: pathlib.Path, title: str | None = None) -> str:
    """Documento mínimo con un único diagrama SVG y su título."""
    heading = title or source.stem.replace("-", " ").replace("_", " ").capitalize()
    return f"# {heading}\n\n![{heading}]({source.name})\n"


def render_html(
    source: pathlib.Path,
    landscape: bool = False,
    paper: str = "A4",
    title: str | None = None,
) -> tuple[str, int]:
    if source.suffix.lower() == ".svg":
        raw = svg_as_markdown(source, title)
    else:
        raw = source.read_text(encoding="utf-8")
    text, diagrams = convert_mermaid_blocks(raw)
    body = unlink_relative_links(
        markdown.markdown(
            text, extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"]
        )
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
        title=html.escape(title or source.stem),
        page_size=f"{paper} landscape" if landscape else paper,
        diagram_height=DIAGRAM_HEIGHT[(paper, landscape)],
        base=source.parent.resolve().as_uri() + "/",
        body=body,
        script=script,
    )
    return page, diagrams


def is_browser_error_page(pdf: bytes) -> bool:
    """Detecta el PDF de la página de error del navegador.

    Si el navegador no llega a abrir el HTML, igual imprime su propia pantalla de error y
    el archivo queda con una sola página inútil. En ese caso el título del PDF es la URL
    del archivo en vez del título del documento.
    """
    return b"/Title (file:///" in pdf


def build(
    source: pathlib.Path,
    output: pathlib.Path,
    landscape: bool = False,
    paper: str = "A4",
    title: str | None = None,
) -> None:
    browsers = find_browsers()
    if not browsers:
        raise SystemExit(
            "No se encontró Edge ni Chrome (definir EDGE_PATH o CHROME_PATH)."
        )
    page, _ = render_html(source, landscape, paper, title)
    output.parent.mkdir(parents=True, exist_ok=True)

    problems: list[str] = []
    for browser in browsers:
        if output.exists():
            # Si el navegador falla, el archivo anterior parecería recién generado.
            output.unlink()
        with tempfile.TemporaryDirectory() as tmp:
            html_path = pathlib.Path(tmp) / "documento.html"
            html_path.write_text(page, encoding="utf-8")
            subprocess.run(
                [str(browser), "--headless=new", "--disable-gpu", "--no-first-run",
                 "--no-pdf-header-footer", "--allow-file-access-from-files",
                 f"--user-data-dir={pathlib.Path(tmp) / 'perfil'}",
                 f"--print-to-pdf={output.resolve()}", "--virtual-time-budget=20000",
                 html_path.as_uri()],
                check=True, capture_output=True, timeout=180,
            )
        if not output.exists() or output.stat().st_size == 0:
            problems.append(f"{browser.name} no escribió el PDF (¿estaba abierto?)")
            continue
        if is_browser_error_page(output.read_bytes()):
            output.unlink()
            problems.append(f"{browser.name} imprimió su página de error")
            continue
        return

    raise SystemExit(
        "Ningún navegador generó el PDF: " + "; ".join(problems) + ". "
        "Cerrá el navegador o indicá otro con EDGE_PATH o CHROME_PATH."
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("markdown", type=pathlib.Path)
    parser.add_argument("-o", "--output", type=pathlib.Path)
    parser.add_argument("--landscape", action="store_true", help="hojas apaisadas")
    parser.add_argument("--paper", choices=("A4", "A3"), default="A4", help="tamaño de hoja")
    parser.add_argument("--title", help="título del PDF cuando la entrada es un .svg")
    args = parser.parse_args()

    output = args.output or HERE.parent / "pdf" / f"{args.markdown.stem}.pdf"
    build(args.markdown, output, args.landscape, args.paper, args.title)
    print(f"PDF generado: {output} ({output.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
