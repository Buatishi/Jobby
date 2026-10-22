"""PDFs mínimos armados a mano para probar la lectura de CVs.

`reportlab` no es una dependencia del backend, así que los PDFs de prueba se escriben
byte a byte. Las coordenadas se dan desde el borde SUPERIOR izquierdo de la hoja (como
se lee un CV); el builder las convierte al origen inferior que usa el formato PDF.
"""

from dataclasses import dataclass, field

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0


@dataclass(frozen=True)
class Text:
    """Una línea de texto; `x` es el borde izquierdo y `top` el borde superior."""

    x: float
    top: float
    text: str
    size: float = 10.0
    bold: bool = False


@dataclass(frozen=True)
class Image:
    """Una imagen de 2x2 píxeles estirada al rectángulo dado (una foto, en un CV)."""

    x: float
    top: float
    width: float
    height: float


@dataclass(frozen=True)
class Line:
    """Un trazo recto, como el borde de una celda de tabla."""

    x0: float
    top0: float
    x1: float
    top1: float


@dataclass
class Page:
    texts: list[Text] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)


def grid_lines(
    x: float, top: float, column_widths: list[float], row_heights: list[float]
) -> list[Line]:
    """Las líneas de una tabla con bordes: una por cada límite de fila y de columna."""
    right = x + sum(column_widths)
    bottom = top + sum(row_heights)
    lines: list[Line] = []
    offset = 0.0
    for height in [0.0, *row_heights]:
        offset += height
        lines.append(Line(x, top + offset, right, top + offset))
    offset = 0.0
    for width in [0.0, *column_widths]:
        offset += width
        lines.append(Line(x + offset, top, x + offset, bottom))
    return lines


def _escape(text: str) -> bytes:
    encoded = text.encode("cp1252")
    return encoded.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _content_stream(page: Page) -> bytes:
    parts: list[bytes] = []
    for image in page.images:
        bottom = PAGE_HEIGHT - image.top - image.height
        parts.append(
            (
                f"q {image.width} 0 0 {image.height} {image.x} {bottom} cm /Im1 Do Q"
            ).encode()
        )
    for line in page.lines:
        parts.append(
            (
                f"0.5 w {line.x0} {PAGE_HEIGHT - line.top0} m "
                f"{line.x1} {PAGE_HEIGHT - line.top1} l S"
            ).encode()
        )
    for text in page.texts:
        font = "F2" if text.bold else "F1"
        baseline = PAGE_HEIGHT - text.top - text.size
        parts.append(
            f"BT /{font} {text.size} Tf {text.x} {baseline} Td (".encode()
            + _escape(text.text)
            + b") Tj ET"
        )
    return b"\n".join(parts)


def build_pdf(pages: list[Page]) -> bytes:
    """Un PDF con las páginas dadas, texto en Helvetica y Helvetica-Bold."""
    # Objetos fijos: 1 catálogo, 2 páginas, 3 y 4 fuentes, 5 imagen.
    page_ids = [6 + 2 * index for index in range(len(pages))]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            "<< /Type /Pages /Kids ["
            + " ".join(f"{page_id} 0 R" for page_id in page_ids)
            + f"] /Count {len(pages)} >>"
        ).encode(),
        3: (
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>"
        ),
        4: (
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            b"/Encoding /WinAnsiEncoding >>"
        ),
        5: (
            b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 "
            b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 12 >>\n"
            b"stream\n" + bytes(range(12)) + b"\nendstream"
        ),
    }
    for page, page_id in zip(pages, page_ids, strict=True):
        stream = _content_stream(page)
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> "
            f"/XObject << /Im1 5 0 R >> >> /Contents {page_id + 1} 0 R >>"
        ).encode()
        objects[page_id + 1] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )

    content = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(content)
        content.extend(f"{number} 0 obj\n".encode())
        content.extend(objects[number])
        content.extend(b"\nendobj\n")

    size = max(objects) + 1
    xref_offset = len(content)
    content.extend(f"xref\n0 {size}\n".encode())
    content.extend(b"0000000000 65535 f \n")
    for number in range(1, size):
        content.extend(f"{offsets[number]:010d} 00000 n \n".encode())
    content.extend(
        (
            f"trailer\n<< /Size {size} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(content)
