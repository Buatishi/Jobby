"""Pruebas de las herramientas de documentación.

    python -m unittest discover -s docs/tools -p "test_*.py" -v
"""

import pathlib
import re
import tempfile
import unittest

from build_pdf import convert_mermaid_blocks, render_html
from tooling import load_lock

HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ConvertMermaidBlocksTest(unittest.TestCase):
    def test_converts_a_block_into_an_escaped_div(self) -> None:
        text = "Antes\n\n```mermaid\nflowchart LR\n  A -->|x & y| B\n```\n\nDespués\n"

        result, count = convert_mermaid_blocks(text)

        self.assertEqual(count, 1)
        self.assertIn('<div class="mermaid">flowchart LR', result)
        self.assertIn("A --&gt;|x &amp; y| B</div>", result)
        self.assertNotIn("```", result)
        self.assertIn("Antes", result)
        self.assertIn("Después", result)

    def test_counts_every_block_and_ignores_other_fences(self) -> None:
        text = (
            "```mermaid\nsequenceDiagram\n```\n\n"
            "```python\nprint('hola')\n```\n\n"
            "```mermaid\nerDiagram\n```\n"
        )

        result, count = convert_mermaid_blocks(text)

        self.assertEqual(count, 2)
        self.assertIn("```python\nprint('hola')\n```", result)

    def test_text_without_blocks_is_unchanged(self) -> None:
        text = "# Título\n\nSolo texto.\n"

        result, count = convert_mermaid_blocks(text)

        self.assertEqual((result, count), (text, 0))


class RenderHtmlTest(unittest.TestCase):
    def test_document_without_diagrams_does_not_load_mermaid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "doc.md"
            source.write_text("# Hola\n\n| a | b |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")

            page, diagrams = render_html(source)

        self.assertEqual(diagrams, 0)
        self.assertIn("<h1", page)
        self.assertIn("<table>", page)
        self.assertNotIn("mermaid.min.js", page)


class LinkTest(unittest.TestCase):
    def test_relative_links_become_text_and_web_links_are_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "doc.md"
            source.write_text(
                "Ver [nivel 1](01-dfd.md), [lámina](pdf/x.pdf), "
                "[repo](https://github.com/Buatishi/Jobby) y [arriba](#titulo).\n",
                encoding="utf-8",
            )

            page, _ = render_html(source)

        self.assertIn("Ver nivel 1, lámina,", page)
        self.assertNotIn('href="01-dfd.md"', page)
        self.assertNotIn('href="pdf/x.pdf"', page)
        self.assertIn('<a href="https://github.com/Buatishi/Jobby">repo</a>', page)
        self.assertIn('<a href="#titulo">arriba</a>', page)


class PageOrientationTest(unittest.TestCase):
    def test_landscape_flag_changes_the_page_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "doc.md"
            source.write_text("# Hola\n", encoding="utf-8")

            portrait, _ = render_html(source)
            landscape, _ = render_html(source, landscape=True)

        self.assertIn("size: A4;", portrait)
        self.assertIn("size: A4 landscape;", landscape)
        self.assertNotIn("landscape", portrait)

    def test_a3_paper_changes_the_page_size_and_the_diagram_height(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "doc.md"
            source.write_text("# Hola\n", encoding="utf-8")

            a3_portrait, _ = render_html(source, paper="A3")
            a3_landscape, _ = render_html(source, landscape=True, paper="A3")

        self.assertIn("size: A3;", a3_portrait)
        self.assertIn("max-height: 330mm", a3_portrait)
        self.assertIn("size: A3 landscape;", a3_landscape)
        self.assertIn("max-height: 225mm", a3_landscape)


class SvgInputTest(unittest.TestCase):
    def test_an_svg_becomes_a_page_with_its_title_and_the_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "dfd-nivel-2.svg"
            source.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")

            page, diagrams = render_html(source, title="DFD nivel 2")

        self.assertEqual(diagrams, 0)
        self.assertIn("<h1", page)
        self.assertIn("DFD nivel 2</h1>", page)
        self.assertIn('src="dfd-nivel-2.svg"', page)
        self.assertIn("<title>DFD nivel 2</title>", page)

    def test_without_a_title_the_file_name_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "modelo-entidad-relacion.svg"
            source.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")

            page, _ = render_html(source)

        self.assertIn("Modelo entidad relacion</h1>", page)


class LockFileTest(unittest.TestCase):
    def test_lock_pins_tools_with_hashes(self) -> None:
        lock = load_lock()

        self.assertRegex(lock["plantuml"]["sha256"], HEX64)
        self.assertRegex(lock["mermaid"]["sha256"], HEX64)
        self.assertTrue(lock["mermaid"]["npm_integrity"].startswith("sha512-"))
        self.assertEqual(lock["mermaid"]["file"], "package/dist/mermaid.min.js")


if __name__ == "__main__":
    unittest.main()
