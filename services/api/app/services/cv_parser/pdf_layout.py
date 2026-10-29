"""Diseño de un CV en PDF: el orden de lectura y las banderas de formato del ATS.

`page.extract_text()` agrupa por renglón de la hoja, así que en un CV de dos columnas
intercala una línea de cada lado («Nombre Apellido EXPERIENCIA LABORAL»). Acá se detecta
el hueco entre columnas y se lee cada columna entera, una después de la otra; una hoja
sin columnas se lee exactamente igual que antes.

La misma pasada devuelve las banderas que el chequeo de formato del ATS
(`ats_analyzer/format_checker.py`) lee de `parsed_data.format_flags`: tablas, varias
columnas, imágenes y títulos de sección. Todo es local (pdfplumber), sin IA ni costo.

Umbrales (se midieron con PDFs sintéticos de una y de dos columnas, ver
`tests/unit/test_pdf_layout.py`; la justificación está en la Decisión 34):

- Una hoja tiene dos columnas si hay un hueco vertical de al menos `MIN_GUTTER_WIDTH`
  puntos que casi ningún renglón cruza (`MAX_CROSSING_SHARE`) y a cada lado hay al menos
  `MIN_COLUMN_LINES` renglones de texto seguidos. Las fechas alineadas a la derecha, las
  viñetas con sangría ancha o un encabezado con el contacto a un costado dejan un hueco
  parecido, pero no tienen una columna de texto del otro lado.
- Una imagen cuenta si ocupa al menos `MIN_IMAGE_AREA_SHARE` de la hoja: una foto o un
  logo sí, los íconos de contacto de las plantillas no.
- Una tabla cuenta si tiene bordes visibles y al menos dos celdas con texto: un recuadro
  o una línea bajo un título no son una tabla.
- Un título de sección es un renglón corto, sin números, con el estilo de título (más
  grande que el cuerpo, o negrita en mayúsculas) que comparten al menos dos renglones.
"""

import math
import re
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from statistics import median
from typing import Any

from pdfplumber.page import Page

# Hueco mínimo entre columnas, en puntos (unos 3,5 mm): cuatro espacios de 10 pt.
MIN_GUTTER_WIDTH = 10.0
# Parte de los renglones que puede cruzar el hueco (el nombre, un título de ancho
# completo).
MAX_CROSSING_SHARE = 0.10
# Renglones seguidos que tiene que tener cada lado para ser una columna y no un adorno.
MIN_COLUMN_LINES = 6
# Dos renglones de una columna están «seguidos» si los separa a lo sumo este múltiplo de
# su separación típica, y esa separación no pasa de este múltiplo del alto del texto.
LINE_GAP_FACTOR = 2.5
# Dos alturas de texto a menos de esto (en puntos) son el mismo renglón.
LINE_TOLERANCE = 3.0
# Dos renglones que arrancan a menos de esto (en puntos) arrancan en el mismo borde.
EDGE_BIN = 4.0
MIN_IMAGE_AREA_SHARE = 0.005
MIN_TABLE_CELLS_WITH_TEXT = 2
# Lado máximo de una hoja analizada, en puntos. El tamaño de la hoja lo declara el PDF y
# `_free_runs` reserva listas del largo del ancho: sin tope, una hoja de 3e7 puntos
# pedía cientos de MB. Un A4 mide 595 x 842 y hasta un A0 (2384 x 3370) entra de sobra.
MAX_PAGE_SIDE = 5_000.0

HEADING_SIZE_FACTOR = 1.2
MAX_HEADING_WORDS = 4
MAX_HEADING_CHARS = 40
MIN_GROUP_LINES = 2
_BOLD_FONT = re.compile(r"bold|black|heavy|semibold|demi", re.IGNORECASE)
_HEADING_SHAPE = re.compile(r"[^\W\d_]+(?:[ &/'’-]+[^\W\d_]+)*")

class PageTooLargeError(ValueError):
    """La hoja declara un tamaño que no es de un CV: no se analiza su diseño."""


Word = dict[str, Any]
# Posición de lectura de un punto: (tramo de arriba abajo, columna dentro del tramo).
ReadingKey = tuple[int, int]
# Posición de un renglón en el documento: hoja, tramo, columna, altura y borde
# izquierdo.
LineOrder = tuple[int, int, int, float, float]


@dataclass(frozen=True)
class FormatFlags:
    has_tables: bool
    multi_column: bool
    has_images: bool
    headers: list[str]

    def to_dict(self) -> dict[str, Any]:
        """La forma que se guarda en `parsed_data.format_flags` y lee el ATS."""
        return {
            "has_tables": self.has_tables,
            "multi_column": self.multi_column,
            "has_images": self.has_images,
            "headers": list(self.headers),
        }


@dataclass(frozen=True)
class PdfContent:
    """Lo que se lee de un PDF. Sin banderas (`None`) el formato no pudo evaluarse."""

    text: str
    format_flags: FormatFlags | None


@dataclass(frozen=True)
class PdfLayout:
    page_texts: list[str]
    format_flags: FormatFlags


@dataclass(frozen=True, eq=False)
class _Segment:
    """Un tramo de un renglón: palabras seguidas sin un hueco de columna entre ellas."""

    x0: float
    x1: float
    top: float
    bottom: float
    words: tuple[Word, ...]

    @property
    def has_text(self) -> bool:
        """Con letras o números de verdad: una viñeta o un guion no son una columna."""
        return any(
            sum(char.isalnum() for char in word["text"]) >= 2 for word in self.words
        )

    @property
    def size(self) -> float:
        return _half_points(max(word["size"] for word in self.words))


@dataclass(frozen=True)
class _Gutter:
    """El hueco entre dos columnas y las franjas de ancho completo que lo cruzan."""

    center: float
    bands: tuple[tuple[float, float], ...]


def _half_points(size: float) -> float:
    return float(round(size * 2) / 2)


def _cluster(values: Iterable[float]) -> list[float]:
    """Agrupa valores cercanos (alturas de renglón) y devuelve uno por grupo."""
    clusters: list[float] = []
    for value in sorted(values):
        if clusters and value - clusters[-1] <= LINE_TOLERANCE:
            continue
        clusters.append(value)
    return clusters


def _segment(words: list[Word]) -> _Segment:
    return _Segment(
        x0=min(word["x0"] for word in words),
        x1=max(word["x1"] for word in words),
        top=min(word["top"] for word in words),
        bottom=max(word["bottom"] for word in words),
        words=tuple(words),
    )


def _segments(words: Sequence[Word]) -> list[_Segment]:
    rows: list[list[Word]] = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        if rows and word["top"] - rows[-1][0]["top"] <= LINE_TOLERANCE:
            rows[-1].append(word)
        else:
            rows.append([word])

    segments: list[_Segment] = []
    for row in rows:
        row.sort(key=lambda item: item["x0"])
        current = [row[0]]
        for word in row[1:]:
            if word["x0"] - current[-1]["x1"] > MIN_GUTTER_WIDTH:
                segments.append(_segment(current))
                current = []
            current.append(word)
        segments.append(_segment(current))
    return segments


# --- columnas -------------------------------------------------------------------------


def _is_column(segments: Sequence[_Segment]) -> bool:
    """¿Estos tramos forman una columna de texto, con renglones seguidos?

    Los renglones de una columna están separados por poco más que el alto de una letra.
    Un renglón cada varios (la fecha de cada cargo, alineada a la derecha) no es una
    columna aunque se repita con regularidad.
    """
    texts = [segment for segment in segments if segment.has_text]
    tops = _cluster(segment.top for segment in texts)
    if len(tops) < MIN_COLUMN_LINES:
        return False
    gaps = [later - earlier for earlier, later in zip(tops, tops[1:], strict=False)]
    pitch = median(gaps)
    text_height = median(segment.bottom - segment.top for segment in texts)
    if pitch > LINE_GAP_FACTOR * text_height:
        return False
    longest = run = 1
    for gap in gaps:
        run = run + 1 if gap <= LINE_GAP_FACTOR * pitch else 1
        longest = max(longest, run)
    return longest >= MIN_COLUMN_LINES


def _free_runs(
    segments: Sequence[_Segment], width: float, tolerance: int
) -> list[tuple[int, int]]:
    """Franjas verticales entre el texto de los dos lados que cruzan pocos renglones."""
    size = math.ceil(width) + 2
    delta = [0] * (size + 1)
    for segment in segments:
        first_bin = max(0, int(segment.x0))
        end_bin = min(size, math.ceil(segment.x1))
        if end_bin > first_bin:
            delta[first_bin] += 1
            delta[end_bin] -= 1
    cover: list[int] = []
    total = 0
    for step in delta[:size]:
        total += step
        cover.append(total)

    occupied = [index for index, count in enumerate(cover) if count > 0]
    if not occupied:
        return []

    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index in range(occupied[0], occupied[-1] + 1):
        if cover[index] <= tolerance:
            if start is None:
                start = index
        elif start is not None:
            runs.append((start, index))
            start = None
    return [run for run in runs if run[1] - run[0] >= MIN_GUTTER_WIDTH]


def _column_edge(segments: Sequence[_Segment], split: float) -> float | None:
    """Dónde empieza la columna derecha: el borde izquierdo común a más renglones."""
    starts = [
        segment.x0 for segment in segments if segment.has_text and segment.x0 >= split
    ]
    if not starts:
        return None
    bins = Counter(int(start // EDGE_BIN) for start in starts)
    densest = bins.most_common(1)[0][0]
    aligned = [start for start in starts if int(start // EDGE_BIN) == densest]
    return float(median(aligned))


def _merge_bands(spans: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    merged: list[tuple[float, float]] = []
    for top, bottom in sorted(spans):
        if merged and top <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], bottom))
        else:
            merged.append((top, bottom))
    return merged


def _find_gutter(segments: Sequence[_Segment], width: float) -> _Gutter | None:
    if len(segments) < 2 * MIN_COLUMN_LINES:
        return None
    tolerance = max(2, int(MAX_CROSSING_SHARE * len(segments)))

    runs = sorted(
        _free_runs(segments, width, tolerance), key=lambda run: run[0] - run[1]
    )
    for start, end in runs:
        split = (start + end) / 2
        edge = _column_edge(segments, split)
        if edge is None:
            continue
        # A la izquierda del hueco, lo que arranca en el borde de la columna derecha y,
        # en el medio, los renglones de ancho completo (el nombre, un título) que se
        # meten en el hueco aunque no pasen justo por su centro.
        left = [segment for segment in segments if segment.x1 <= split]
        right = [segment for segment in segments if segment.x0 >= edge - EDGE_BIN]
        crossing = [
            segment
            for segment in segments
            if segment.x1 > split and segment.x0 < edge - EDGE_BIN
        ]
        if not left or len(crossing) > tolerance:
            continue
        gutter_start = max(segment.x1 for segment in left)
        if edge - gutter_start < MIN_GUTTER_WIDTH:
            continue
        if not (_is_column(left) and _is_column(right)):
            continue
        return _Gutter(
            center=(gutter_start + edge) / 2,
            bands=tuple(_merge_bands((s.top, s.bottom) for s in crossing)),
        )
    return None


def _reading_key(gutter: _Gutter, x_center: float, y_center: float) -> ReadingKey:
    """Dónde se lee un punto; las franjas de ancho completo cortan el orden."""
    stretch = 0
    for index, (top, bottom) in enumerate(gutter.bands):
        if top - 1 <= y_center <= bottom + 1:
            return (2 * index + 1, 0)
        if y_center > bottom:
            stretch = index + 1
    return (2 * stretch, 0 if x_center < gutter.center else 1)


def _page_text(page: Page, gutter: _Gutter | None) -> str:
    if gutter is None:
        return page.extract_text() or ""

    def key_of(obj: Word) -> ReadingKey:
        return _reading_key(
            gutter,
            (obj["x0"] + obj["x1"]) / 2,
            (obj["top"] + obj["bottom"]) / 2,
        )

    def only(key: ReadingKey) -> Callable[[Word], bool]:
        return lambda obj: obj.get("object_type") != "char" or key_of(obj) == key

    parts = [
        page.filter(only(key)).extract_text() or ""
        for key in sorted({key_of(char) for char in page.chars})
    ]
    return "\n".join(part for part in parts if part.strip())


# --- imágenes y tablas ----------------------------------------------------------------


def _has_images(page: Page) -> bool:
    minimum = MIN_IMAGE_AREA_SHARE * page.width * page.height
    for image in page.images:
        width = min(image["x1"], page.width) - max(image["x0"], 0)
        height = min(image["bottom"], page.height) - max(image["top"], 0)
        if width > 0 and height > 0 and width * height >= minimum:
            return True
    return False


def _has_tables(page: Page) -> bool:
    for table in page.find_tables():
        with_text = sum(
            1 for row in table.extract() for cell in row if cell and cell.strip()
        )
        if with_text >= MIN_TABLE_CELLS_WITH_TEXT:
            return True
    return False


# --- títulos de sección ---------------------------------------------------------------


@dataclass(frozen=True)
class _Line:
    text: str
    size: float
    bold: bool
    order: LineOrder

    @property
    def style(self) -> tuple[float, bool, bool]:
        return (self.size, self.bold, self.text.isupper())


def _line_of(segment: _Segment, order: LineOrder) -> _Line:
    return _Line(
        text=" ".join(word["text"] for word in segment.words),
        size=segment.size,
        bold=all(_BOLD_FONT.search(str(word["fontname"])) for word in segment.words),
        order=order,
    )


def _looks_like_a_title(text: str) -> bool:
    title = text.strip().removesuffix(":").strip()
    return (
        len(title) <= MAX_HEADING_CHARS
        and len(title.split()) <= MAX_HEADING_WORDS
        and sum(char.isalpha() for char in title) >= 3
        and _HEADING_SHAPE.fullmatch(title) is not None
    )


def _body_size(pages_words: Iterable[Sequence[Word]]) -> float | None:
    """El tamaño de letra con más texto del documento: el del cuerpo."""
    weights: Counter[float] = Counter()
    for words in pages_words:
        for word in words:
            weights[_half_points(word["size"])] += len(word["text"])
    return weights.most_common(1)[0][0] if weights else None


def _identity_segments(segments: Sequence[_Segment]) -> list[_Segment]:
    """El texto más grande de la primera hoja, casi siempre el nombre.

    Si otro renglón comparte su tamaño y su altura (el nombre y el título de la barra
    lateral, en la misma fila) también queda afuera: es mejor perder un título que
    contar el nombre como si lo fuera.
    """
    if not segments:
        return []
    largest = max(
        segments, key=lambda segment: (segment.size, -segment.top, -segment.x0)
    )
    return [
        segment
        for segment in segments
        if segment.size == largest.size
        and abs(segment.top - largest.top) <= LINE_TOLERANCE
    ]


def _section_titles(lines: Sequence[_Line], body_size: float | None) -> list[str]:
    """Los títulos de sección: renglones cortos con el estilo de título que se repite.

    Prioriza no equivocarse: marcar de más le resta puntos a quien no los merece. Solo
    cuenta el estilo (tamaño, negrita, mayúsculas) que comparten al menos dos renglones:
    el nombre y el cargo, únicos en el suyo, quedan afuera; también la negrita del
    tamaño del cuerpo (un cargo) y un CV con un solo título, que no se distingue del
    nombre.
    """
    if body_size is None:
        return []
    candidates = [
        line
        for line in lines
        if _looks_like_a_title(line.text)
        and (
            line.size >= HEADING_SIZE_FACTOR * body_size
            or (line.bold and line.text.upper() == line.text)
        )
    ]
    styles = Counter(line.style for line in candidates)
    titles = [
        line.text.strip().removesuffix(":").strip()
        for line in sorted(candidates, key=lambda item: item.order)
        if styles[line.style] >= MIN_GROUP_LINES
    ]
    return list(dict.fromkeys(titles))


# --- lectura de todo el PDF -----------------------------------------------------------


def read_layout(pages: Sequence[Page]) -> PdfLayout:
    page_texts: list[str] = []
    pages_words: list[list[Word]] = []
    lines: list[_Line] = []
    has_tables = has_images = multi_column = False

    for number, page in enumerate(pages):
        width = float(page.width)
        if width > MAX_PAGE_SIDE or float(page.height) > MAX_PAGE_SIDE:
            # `_read_pages` cae a la lectura plana: el CV se sigue leyendo.
            raise PageTooLargeError("El tamaño de la hoja supera el de un documento.")
        words = page.extract_words(extra_attrs=["fontname", "size"])
        segments = _segments(words)
        gutter = _find_gutter(segments, width)
        multi_column = multi_column or gutter is not None
        page_texts.append(_page_text(page, gutter))
        has_images = has_images or _has_images(page)
        has_tables = has_tables or _has_tables(page)
        pages_words.append(words)

        identity = _identity_segments(segments) if number == 0 else []
        for segment in segments:
            if any(segment is skipped for skipped in identity):
                continue
            key = (0, 0)
            if gutter is not None:
                key = _reading_key(
                    gutter,
                    (segment.x0 + segment.x1) / 2,
                    (segment.top + segment.bottom) / 2,
                )
            lines.append(
                _line_of(segment, (number, key[0], key[1], segment.top, segment.x0))
            )

    flags = FormatFlags(
        has_tables=has_tables,
        multi_column=multi_column,
        has_images=has_images,
        headers=_section_titles(lines, _body_size(pages_words)),
    )
    return PdfLayout(page_texts=page_texts, format_flags=flags)
