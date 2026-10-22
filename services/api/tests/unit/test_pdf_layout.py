"""Qué se lee de un CV en PDF: el texto en orden de lectura y las banderas de formato.

Antes `page.extract_text()` intercalaba los renglones de un CV de dos columnas («Nombre
Apellido EXPERIENCIA LABORAL») y nada guardaba si el CV tenía tablas, columnas o
imágenes, así que el chequeo de formato del ATS nunca corría. Los PDFs se arman a mano
(`tests/pdf_builder.py`): `reportlab` no es una dependencia del backend.
"""

from pathlib import Path

import pdfplumber
import pytest

from app.services.cv_parser import (
    CVParsingError,
    FormatFlags,
    PdfContent,
    extract_pdf_content,
    extract_pdf_text,
    pdf_extractor,
)
from tests.pdf_builder import Image, Line, Page, Text, build_pdf, grid_lines


def _write(tmp_path: Path, *pages: Page) -> Path:
    path = tmp_path / "cv.pdf"
    path.write_bytes(build_pdf(list(pages)))
    return path


def _heading(x: float, top: float, text: str) -> Text:
    return Text(x, top, text, size=12, bold=True)


def _body(x: float, top: float, lines: list[str]) -> list[Text]:
    return [Text(x, top + 14 * index, line) for index, line in enumerate(lines)]


def single_column_page() -> Page:
    """Un CV prolijo de una columna: nombre, contacto y tres secciones."""
    texts = [
        Text(60, 50, "Nombre Apellido", size=20, bold=True),
        Text(60, 80, "juan@example.com - Buenos Aires"),
    ]
    top = 110.0
    sections = [
        ("EXPERIENCIA", ["Desarrollador Backend en Acme", "APIs con FastAPI"]),
        ("EDUCACION", ["Ingenieria en Sistemas, UTN"]),
        ("HABILIDADES", ["Python, SQL, Git, Linux, React, Docker"]),
    ]
    for title, lines in sections:
        texts.append(_heading(60, top, title))
        texts.extend(_body(60, top + 20, lines))
        top += 20 + 14 * len(lines) + 16
    return Page(texts=texts)


SIDEBAR = ["Python", "SQL", "Git", "Linux", "React", "Docker"]


def two_column_page(*, photo: bool = True, sidebar_x: float = 40) -> Page:
    """La plantilla de dos columnas con foto: barra lateral y columna principal."""
    left = [
        _heading(sidebar_x, 60, "CONTACTO"),
        *_body(sidebar_x, 80, ["juan@example.com", "Buenos Aires"]),
        _heading(sidebar_x, 130, "HABILIDADES"),
        *_body(sidebar_x, 150, SIDEBAR),
    ]
    right = [
        Text(230, 60, "Nombre Apellido", size=20, bold=True),
        _heading(230, 100, "PERFIL ACADEMICO"),
        *_body(
            230,
            120,
            ["Estudiante de Ingenieria en Sistemas", "en la Universidad Tecnologica"],
        ),
        _heading(230, 170, "EXPERIENCIA LABORAL"),
        *_body(
            230,
            190,
            [
                "Desarrollador Backend en Acme",
                "Construccion de APIs con FastAPI",
                "Mantenimiento de bases PostgreSQL",
            ],
        ),
    ]
    images = [Image(sidebar_x, 250, 100, 120)] if photo else []
    return Page(texts=left + right, images=images)


def banner_then_two_columns_page() -> Page:
    """El nombre ocupa todo el ancho y recién abajo empiezan las dos columnas."""
    page = two_column_page(photo=False)
    page.texts = [text for text in page.texts if text.text != "Nombre Apellido"]
    page.texts.append(Text(190, 24, "Nombre Apellido Completo", size=20, bold=True))
    return page


def dated_one_column_page() -> Page:
    """Una columna con renglones cortos y fechas a la derecha (no son columnas)."""
    texts = [Text(60, 50, "Nombre Apellido", size=20, bold=True)]
    top = 90.0
    for index in range(8):
        texts.append(Text(60, top, f"Empresa {index + 1}", size=10, bold=True))
        texts.append(Text(430, top, "Ene 2020 - Mar 2022"))
        texts.extend(_body(60, top + 14, ["Tareas del cargo", "Otro logro"]))
        top += 14 * 3 + 14
    return Page(texts=texts)


def bulleted_page() -> Page:
    """Viñetas con sangría ancha: el hueco hasta el texto no es una columna."""
    texts = [Text(60, 50, "Nombre Apellido", size=20, bold=True)]
    for index in range(12):
        top = 90 + 14 * index
        texts.append(Text(60, top, "•"))
        texts.append(Text(90, top, f"Logro numero {index + 1} del cargo"))
    return Page(texts=texts)


def _plain_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n\n".join(page.extract_text() or "" for page in pdf.pages)


# --- orden de lectura -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_columns_are_read_one_after_the_other(tmp_path: Path) -> None:
    path = _write(tmp_path, two_column_page())

    # El caso que se leía mal: la lectura plana mezcla los renglones de las columnas.
    assert "CONTACTO Nombre Apellido" in _plain_text(path)

    text = await extract_pdf_text(path)

    assert "CONTACTO Nombre Apellido" not in text
    assert "Python\nSQL\nGit\nLinux\nReact\nDocker" in text
    assert (
        "Desarrollador Backend en Acme\n"
        "Construccion de APIs con FastAPI\n"
        "Mantenimiento de bases PostgreSQL"
    ) in text
    assert "Estudiante de Ingenieria en Sistemas\nen la Universidad Tecnologica" in text
    # La columna izquierda entera va antes que la derecha.
    assert text.index("Docker") < text.index("Nombre Apellido")


@pytest.mark.asyncio
async def test_a_narrow_sidebar_next_to_a_wide_column_is_read_in_order(
    tmp_path: Path,
) -> None:
    """Barra de ~70 pt a la izquierda y la columna principal ocupando el resto."""
    sidebar = [Text(30, 60 + 14 * index, word) for index, word in enumerate(SIDEBAR)]
    main = [
        Text(130, 60 + 14 * index, line)
        for index, line in enumerate(
            [
                "Estudiante de Ingenieria en Sistemas en la Universidad Tecnologica",
                "Desarrollador Backend en Acme con foco en servicios de pago online",
                "Construccion de APIs con FastAPI y bases de datos PostgreSQL",
                "Mantenimiento de pipelines de integracion y despliegue continuo",
                "Revision de codigo, mentoria y documentacion tecnica del equipo",
                "Monitoreo de servicios en produccion con alertas automaticas",
            ]
        )
    ]

    text = await extract_pdf_text(_write(tmp_path, Page(texts=sidebar + main)))

    assert "Python\nSQL\nGit\nLinux\nReact\nDocker" in text
    assert text.index("Docker") < text.index("Estudiante")
    assert "Desarrollador Backend en Acme con foco en servicios de pago online" in text


@pytest.mark.asyncio
async def test_a_full_width_name_stays_in_one_line_above_the_columns(
    tmp_path: Path,
) -> None:
    text = await extract_pdf_text(_write(tmp_path, banner_then_two_columns_page()))

    assert text.startswith("Nombre Apellido Completo\n")
    assert "Python\nSQL\nGit\nLinux\nReact\nDocker" in text
    assert text.index("Nombre Apellido Completo") < text.index("CONTACTO")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "page_factory",
    [single_column_page, dated_one_column_page, bulleted_page],
)
async def test_one_column_text_is_read_exactly_as_before(
    tmp_path: Path, page_factory: object
) -> None:
    path = _write(tmp_path, page_factory())  # type: ignore[operator]

    assert await extract_pdf_text(path) == _plain_text(path).strip()


@pytest.mark.asyncio
async def test_pages_are_joined_and_each_page_picks_its_own_layout(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path, single_column_page(), two_column_page())

    text = await extract_pdf_text(path)

    first_page, second_page = text.split("\n\n", 1)[0], text
    assert "EXPERIENCIA\nDesarrollador Backend en Acme" in first_page
    assert "Python\nSQL\nGit\nLinux\nReact\nDocker" in second_page


# --- banderas de formato --------------------------------------------------------------


async def _flags(path: Path) -> FormatFlags:
    content = await extract_pdf_content(path)
    assert isinstance(content, PdfContent)
    assert content.format_flags is not None
    return content.format_flags


@pytest.mark.asyncio
async def test_a_clean_one_column_cv_has_no_format_problems(tmp_path: Path) -> None:
    flags = await _flags(_write(tmp_path, single_column_page()))

    assert (flags.has_tables, flags.multi_column, flags.has_images) == (
        False,
        False,
        False,
    )
    assert flags.headers == ["EXPERIENCIA", "EDUCACION", "HABILIDADES"]


@pytest.mark.asyncio
async def test_a_two_column_cv_with_a_photo_is_flagged(tmp_path: Path) -> None:
    flags = await _flags(_write(tmp_path, two_column_page()))

    assert flags.multi_column is True
    assert flags.has_images is True
    assert flags.has_tables is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "page_factory",
    [single_column_page, dated_one_column_page, bulleted_page],
)
async def test_one_column_layouts_are_never_called_multi_column(
    tmp_path: Path, page_factory: object
) -> None:
    """Fechas a la derecha, viñetas y encabezados con contacto no son columnas."""
    flags = await _flags(_write(tmp_path, page_factory()))  # type: ignore[operator]

    assert flags.multi_column is False


@pytest.mark.asyncio
async def test_a_banner_above_two_columns_still_counts_as_columns(
    tmp_path: Path,
) -> None:
    flags = await _flags(_write(tmp_path, banner_then_two_columns_page()))

    assert flags.multi_column is True


@pytest.mark.asyncio
async def test_columns_on_only_one_page_flag_the_whole_cv(tmp_path: Path) -> None:
    flags = await _flags(_write(tmp_path, single_column_page(), two_column_page()))

    assert flags.multi_column is True


@pytest.mark.asyncio
async def test_a_header_with_the_contact_block_on_the_right_is_not_a_column(
    tmp_path: Path,
) -> None:
    """Nombre a la izquierda y 5 renglones de contacto a la derecha, texto abajo."""
    page = single_column_page()
    contact = [
        "juan@example.com",
        "+54 11 5555 5555",
        "Buenos Aires",
        "linkedin.com/in/j",
    ]
    page.texts.extend(
        Text(430, 50 + 14 * index, line) for index, line in enumerate(contact)
    )

    flags = await _flags(_write(tmp_path, page))

    assert flags.multi_column is False


@pytest.mark.asyncio
async def test_a_photo_is_an_image_but_an_icon_is_not(tmp_path: Path) -> None:
    icon = single_column_page()
    icon.images.append(Image(60, 600, 12, 12))
    photo = single_column_page()
    photo.images.append(Image(450, 40, 90, 110))

    assert (await _flags(_write(tmp_path, icon))).has_images is False
    assert (await _flags(_write(tmp_path, photo))).has_images is True


@pytest.mark.asyncio
async def test_a_bordered_table_is_flagged(tmp_path: Path) -> None:
    page = single_column_page()
    page.lines.extend(grid_lines(60, 400, [150, 150], [24, 24, 24]))
    cells = [("Python", "Avanzado"), ("SQL", "Medio"), ("Git", "Avanzado")]
    for row, (name, level) in enumerate(cells):
        page.texts.append(Text(68, 406 + 24 * row, name))
        page.texts.append(Text(218, 406 + 24 * row, level))

    flags = await _flags(_write(tmp_path, page))

    assert flags.has_tables is True


@pytest.mark.asyncio
async def test_rules_and_boxes_are_not_tables(tmp_path: Path) -> None:
    """Una línea bajo cada título y un recuadro alrededor del texto no son una tabla."""
    page = single_column_page()
    for top in (128, 190, 240):
        page.lines.append(Line(60, top, 550, top))
    page.lines.extend(grid_lines(60, 400, [300], [60]))
    page.texts.append(Text(68, 410, "Un recuadro con texto adentro"))

    flags = await _flags(_write(tmp_path, page))

    assert flags.has_tables is False


@pytest.mark.asyncio
async def test_headers_are_the_section_titles_not_the_name_or_the_body(
    tmp_path: Path,
) -> None:
    flags = await _flags(_write(tmp_path, two_column_page()))

    assert flags.headers == [
        "CONTACTO",
        "HABILIDADES",
        "PERFIL ACADEMICO",
        "EXPERIENCIA LABORAL",
    ]


@pytest.mark.asyncio
async def test_the_name_is_not_a_header_even_when_it_looks_like_one(
    tmp_path: Path,
) -> None:
    page = single_column_page()
    page.texts[0] = _heading(60, 50, "NOMBRE APELLIDO")

    flags = await _flags(_write(tmp_path, page))

    assert flags.headers == ["EXPERIENCIA", "EDUCACION", "HABILIDADES"]


@pytest.mark.asyncio
async def test_bold_text_at_body_size_is_not_a_header(tmp_path: Path) -> None:
    """Un cargo en negrita («Desarrollador Backend») no es el título de una sección."""
    page = single_column_page()
    page.texts.extend(
        [
            Text(60, 330, "Desarrollador Backend", bold=True),
            Text(60, 400, "Analista Funcional", bold=True),
        ]
    )

    flags = await _flags(_write(tmp_path, page))

    assert flags.headers == ["EXPERIENCIA", "EDUCACION", "HABILIDADES"]


@pytest.mark.asyncio
async def test_a_single_title_is_not_enough_to_tell_it_from_the_name(
    tmp_path: Path,
) -> None:
    page = Page(
        texts=[
            Text(60, 50, "Nombre Apellido", size=20, bold=True),
            _heading(60, 100, "PERFIL ACADEMICO"),
            *_body(60, 120, ["Ingenieria en Sistemas"]),
        ]
    )

    flags = await _flags(_write(tmp_path, page))

    assert flags.headers == []


@pytest.mark.asyncio
async def test_format_flags_serialize_to_the_shape_the_ats_reads() -> None:
    flags = FormatFlags(
        has_tables=True, multi_column=False, has_images=True, headers=["Perfil"]
    )

    assert flags.to_dict() == {
        "has_tables": True,
        "multi_column": False,
        "has_images": True,
        "headers": ["Perfil"],
    }


# --- nada de esto puede romper una lectura que antes funcionaba -----------------------


@pytest.mark.asyncio
async def test_a_layout_failure_falls_back_to_plain_text_without_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, two_column_page())

    def broken(_pages: object) -> PdfContent:
        raise RuntimeError("fallo inesperado del análisis")

    monkeypatch.setattr(pdf_extractor, "read_layout", broken)

    content = await extract_pdf_content(path)

    assert content.text == _plain_text(path).strip()
    # Sin banderas: el ATS dirá «no se pudo evaluar» en vez de «sin problemas».
    assert content.format_flags is None


@pytest.mark.asyncio
async def test_extract_pdf_text_is_the_text_of_the_content(tmp_path: Path) -> None:
    path = _write(tmp_path, two_column_page())

    assert await extract_pdf_text(path) == (await extract_pdf_content(path)).text


@pytest.mark.asyncio
async def test_a_pdf_without_text_still_raises_the_same_error(tmp_path: Path) -> None:
    path = _write(tmp_path, Page(images=[Image(0, 0, 600, 780)]))

    with pytest.raises(CVParsingError) as exc_info:
        await extract_pdf_content(path)

    assert exc_info.value.code == "PDF_EMPTY_TEXT"
