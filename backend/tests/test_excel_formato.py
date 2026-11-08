from io import BytesIO

import pytest
from faker import Faker
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from PIL import Image
from sqlalchemy.orm import Session

from app.models import (
    Actividad,
    Asignacion,
    Colaborador,
    Dia,
    Firmante,
    Foto,
    Herramienta,
    Reporte,
)
from app.services import excel_formato
from app.services.excel_formato import EMU_POR_PIXEL, generar_formato


def _reporte(session: Session, faker: Faker, semana: int = 43) -> Reporte:
    colaboradores = [
        Colaborador(nombre=faker.name(), orden=-1000 - semana + indice) for indice in range(1, 3)
    ]
    herramienta = Herramienta(nombre=faker.word(), orden=1)
    reporte = Reporte(anio=2026, semana=semana)
    reporte.dias = [
        Dia(dia_semana=indice, fecha=faker.date_between(start_date="+1d", end_date="+30d"))
        for indice in range(6)
    ]
    reporte.dias[0].actividades = [
        Actividad(
            letra="A",
            descripcion=faker.sentence(),
            asignaciones=[Asignacion(colaborador=colaboradores[0], horas=4, horas_manual=False)],
        ),
        Actividad(
            letra="B",
            descripcion=faker.sentence(),
            asignaciones=[Asignacion(colaborador=colaboradores[0], horas=4, horas_manual=False)],
        ),
    ]
    session.add_all([*colaboradores, herramienta, reporte])
    session.commit()
    return reporte


def test_formato_tiene_hojas_celdas_y_formulas(session: Session, faker: Faker) -> None:
    reporte = _reporte(session, faker)
    libro = load_workbook(BytesIO(generar_formato(reporte)), data_only=False)

    assert libro.sheetnames == [
        "Lunes",
        "Martes",
        "Miercoles",
        "Jueves",
        "Viernes",
        "Sabado",
        "Datos",
    ]
    lunes = libro["Lunes"]
    assert lunes["I6"].value == 43
    assert lunes["H10"].value == "A, B"
    assert lunes["M11"].value.startswith("=COUNTIF")
    assert lunes["M13"].value == 4
    assert lunes.print_area == "'Lunes'!$A$1:$T$58"
    assert libro["Martes"].print_area == "'Martes'!$A$1:$T$54"
    assert libro["Datos"]["E8"].value == "=+Lunes!M19+Lunes!N19+Lunes!O19"
    assert libro["Datos"]["K8"].value == "=SUM(E8:J8)"


def test_formato_conserva_letra_de_colaborador(session: Session, faker: Faker) -> None:
    reporte = _reporte(session, faker, semana=44)
    libro = load_workbook(BytesIO(generar_formato(reporte)))

    lunes = libro["Lunes"]
    assert "A, B" in [lunes.cell(fila, 8).value for fila in range(10, 23)]
    assert libro["Lunes"]["D26"].value == reporte.dias[0].actividades[0].descripcion


def test_formato_inserta_actividades_d_y_e(session: Session, faker: Faker) -> None:
    reporte = _reporte(session, faker, semana=8)
    descripciones = {letra: faker.sentence() for letra in "CDE"}
    reporte.dias[0].actividades.extend(
        Actividad(letra=letra, descripcion=descripcion)
        for letra, descripcion in descripciones.items()
    )
    firmante = Firmante(nombre=faker.name(), tipo="elabora")
    reporte.elaborado_por = firmante
    session.commit()

    libro = load_workbook(BytesIO(generar_formato(reporte)), data_only=False)
    lunes = libro["Lunes"]

    assert lunes["M24"].value == "D"
    assert lunes["N24"].value == "E"
    assert lunes["M35"].value == "D"
    assert lunes["M36"].value == "E"
    assert lunes["D35"].value == descripciones["D"]
    assert lunes["A37"].value == 6
    assert "M27" in lunes["M17"].value
    assert "N27" in lunes["M17"].value
    assert lunes.print_area == "'Lunes'!$A$1:$T$65"
    assert libro["Datos"]["E8"].value.endswith("+Lunes!M28+Lunes!N28")
    assert "D35:L35" in {str(rango) for rango in lunes.merged_cells.ranges}
    assert lunes["F64"].value == firmante.nombre


def test_formato_inserta_tres_bandas_hasta_j(session: Session, faker: Faker) -> None:
    reporte = _reporte(session, faker, semana=9)
    reporte.dias[0].actividades.extend(
        Actividad(letra=letra, descripcion=faker.sentence()) for letra in "CDEFGHIJ"
    )
    session.commit()

    libro = load_workbook(BytesIO(generar_formato(reporte)), data_only=False)
    lunes = libro["Lunes"]

    assert [lunes.cell(24, columna).value for columna in range(13, 16)] == list("DEF")
    assert [lunes.cell(29, columna).value for columna in range(13, 16)] == list("GHI")
    assert lunes["M34"].value == "J"
    assert lunes["M51"].value == "J"
    assert lunes.print_area == "'Lunes'!$A$1:$T$80"
    assert libro["Datos"]["E8"].value.endswith(
        "+Lunes!M28+Lunes!N28+Lunes!O28+Lunes!M33+Lunes!N33+Lunes!O33+Lunes!M38"
    )


@pytest.mark.parametrize(
    ("letras", "semana", "desplazamiento"),
    (("AB", 12, 0), ("ABCDE", 13, 7), ("ABCDEFGHIJ", 14, 22)),
)
def test_formato_no_oculta_filas_insertadas(
    session: Session,
    faker: Faker,
    letras: str,
    semana: int,
    desplazamiento: int,
) -> None:
    reporte = _reporte(session, faker, semana=semana)
    reporte.dias[0].actividades.extend(
        Actividad(letra=letra, descripcion=faker.sentence()) for letra in letras[2:]
    )
    session.commit()

    lunes = load_workbook(BytesIO(generar_formato(reporte)))["Lunes"]
    ocultas = {
        fila for fila in range(1, lunes.max_row + 1) if lunes.row_dimensions[fila].hidden is True
    }

    assert not ocultas.intersection(range(24, 32 + desplazamiento))
    assert ocultas == set(range(37 + desplazamiento, 51 + desplazamiento))


def test_formato_rellena_huecos_hasta_actividad_mas_alta(session: Session, faker: Faker) -> None:
    reporte = _reporte(session, faker, semana=10)
    descripcion_d = faker.sentence()
    reporte.dias[0].actividades = [
        reporte.dias[0].actividades[0],
        Actividad(letra="D", descripcion=descripcion_d),
    ]
    session.commit()

    lunes = load_workbook(BytesIO(generar_formato(reporte)))["Lunes"]

    assert lunes["D32"].value is None
    assert lunes["D34"].value is None
    assert lunes["D35"].value == descripcion_d


def test_formato_escapa_formula_en_actividad_extra(session: Session, faker: Faker) -> None:
    reporte = _reporte(session, faker, semana=11)
    reporte.dias[0].actividades.append(Actividad(letra="D", descripcion="=1+1"))
    session.commit()

    lunes = load_workbook(BytesIO(generar_formato(reporte)), data_only=False)["Lunes"]

    assert lunes["D35"].value == "'=1+1"


def _pixeles_columna(hoja, indice: int) -> int:
    ancho = hoja.column_dimensions[get_column_letter(indice)].width or 8.43
    return int(ancho * 7 + 5)


def _pixeles_fila(hoja, fila: int) -> int:
    alto = hoja.row_dimensions[fila].height or 15
    return int(alto * 96 / 72)


def _rectangulo(hoja, imagen, fila_inicio: int) -> tuple[float, float, float, float]:
    marcador = imagen.anchor._from
    x = sum(_pixeles_columna(hoja, columna) for columna in range(14, marcador.col + 1))
    y = sum(_pixeles_fila(hoja, fila) for fila in range(fila_inicio, marcador.row + 1))
    x += marcador.colOff / EMU_POR_PIXEL
    y += marcador.rowOff / EMU_POR_PIXEL
    return (
        x,
        y,
        x + imagen.anchor.ext.cx / EMU_POR_PIXEL,
        y + imagen.anchor.ext.cy / EMU_POR_PIXEL,
    )


@pytest.mark.parametrize(
    ("espacio", "cantidad", "fila_inicio", "fila_fin", "semana"),
    (
        ("A", 1, 26, 26, 1),
        ("A", 2, 26, 26, 2),
        ("A", 4, 26, 26, 3),
        ("B", 1, 27, 28, 4),
        ("B", 2, 27, 28, 5),
        ("B", 4, 27, 28, 6),
        ("D", 4, 35, 35, 7),
    ),
)
def test_formato_acomoda_fotos_sin_salirse_ni_superponerse(
    session: Session,
    faker: Faker,
    tmp_path,
    monkeypatch,
    espacio: str,
    cantidad: int,
    fila_inicio: int,
    fila_fin: int,
    semana: int,
) -> None:
    reporte = _reporte(session, faker, semana=semana)
    if espacio == "D":
        reporte.dias[0].actividades.extend(
            [
                Actividad(letra="C", descripcion=faker.sentence()),
                Actividad(letra="D", descripcion=faker.sentence()),
            ]
        )
    for orden in range(1, cantidad + 1):
        nombre = f"foto-{espacio}-{orden}.png"
        Image.new("RGB", (120 + orden, 90 + orden), "green").save(tmp_path / nombre)
        reporte.dias[0].fotos.append(
            Foto(
                espacio=espacio,
                orden=orden,
                archivo=nombre,
                nombre_original=nombre,
            )
        )
    session.commit()
    monkeypatch.setattr(excel_formato, "FOTOS_DIR", tmp_path)

    lunes = load_workbook(BytesIO(generar_formato(reporte)))["Lunes"]
    fotos = lunes._images[:-2]
    rectangulos = [_rectangulo(lunes, imagen, fila_inicio) for imagen in fotos]
    ancho_area = sum(_pixeles_columna(lunes, columna) for columna in range(14, 21))
    alto_area = sum(_pixeles_fila(lunes, fila) for fila in range(fila_inicio, fila_fin + 1))

    assert len(fotos) == cantidad
    assert all(0 <= x1 < x2 <= ancho_area for x1, _, x2, _ in rectangulos)
    assert all(0 <= y1 < y2 <= alto_area for _, y1, _, y2 in rectangulos)
    for indice, primero in enumerate(rectangulos):
        for segundo in rectangulos[indice + 1 :]:
            assert (
                primero[2] <= segundo[0]
                or segundo[2] <= primero[0]
                or primero[3] <= segundo[1]
                or segundo[3] <= primero[1]
            )
    if cantidad == 4 and fila_inicio == fila_fin:
        assert all(y2 - y1 <= alto_area / 2 for _, y1, _, y2 in rectangulos)
