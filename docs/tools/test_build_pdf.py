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


class LockFileTest(unittest.TestCase):
    def test_lock_pins_tools_with_hashes(self) -> None:
        lock = load_lock()

        self.assertRegex(lock["plantuml"]["sha256"], HEX64)
        self.assertRegex(lock["mermaid"]["sha256"], HEX64)
        self.assertTrue(lock["mermaid"]["npm_integrity"].startswith("sha512-"))
        self.assertEqual(lock["mermaid"]["file"], "package/dist/mermaid.min.js")


if __name__ == "__main__":
    unittest.main()
