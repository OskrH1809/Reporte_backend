from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.drawing.spreadsheet_drawing import (
    AnchorMarker,
    OneCellAnchor,
    TwoCellAnchor,
    XDRPositiveSize2D,
)
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import select
from sqlalchemy.orm import object_session

from app.models import Colaborador, Dia, Herramienta, Reporte

PLANTILLAS_DIR = Path(__file__).resolve().parents[1] / "plantillas"
NOMBRES_DIAS = ("Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado")
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
EMU_POR_PIXEL = 9525


def texto_seguro(valor: str) -> str:
    return f"'{valor}" if valor.startswith(FORMULA_PREFIXES) else valor


def _anclar_logo(hoja: Worksheet) -> None:
    imagen = ExcelImage(PLANTILLAS_DIR / "logo.png")
    imagen.anchor = TwoCellAnchor(
        _from=AnchorMarker(col=17, row=0),
        to=AnchorMarker(col=18, colOff=779318, row=3, rowOff=269733),
    )
    hoja.add_image(imagen)


def _anclar_mapa(hoja: Worksheet, con_actividades: bool) -> None:
    fila = 34 if con_actividades else 30
    imagen = ExcelImage(PLANTILLAS_DIR / "mapa.png")
    imagen.anchor = TwoCellAnchor(
        _from=AnchorMarker(col=9, colOff=484907, row=fila, rowOff=154376),
        to=AnchorMarker(col=17, colOff=744681, row=fila + 1, rowOff=3661929),
    )
    hoja.add_image(imagen)


def _pixeles_columna(hoja: Worksheet, indice: int) -> int:
    ancho = hoja.column_dimensions[get_column_letter(indice)].width or 8.43
    return int(ancho * 7 + 5)


def _pixeles_fila(hoja: Worksheet, fila: int) -> int:
    alto = hoja.row_dimensions[fila].height or 15
    return int(alto * 96 / 72)


def _anclar_foto(hoja: Worksheet, ruta: Path, fila: int, derecha: bool) -> None:
    columna_inicio, columna_fin = (18, 20) if derecha else (14, 17)
    ancho = sum(_pixeles_columna(hoja, indice) for indice in range(columna_inicio, columna_fin + 1))
    alto = _pixeles_fila(hoja, fila)
    imagen = ExcelImage(ruta)
    escala = min(ancho / imagen.width, alto / imagen.height)
    imagen.width = max(1, int(imagen.width * escala))
    imagen.height = max(1, int(imagen.height * escala))
    desplazamiento_x = max(0, (ancho - imagen.width) // 2)
    desplazamiento_y = max(0, (alto - imagen.height) // 2)
    imagen.anchor = OneCellAnchor(
        _from=AnchorMarker(
            col=columna_inicio - 1,
            colOff=desplazamiento_x * EMU_POR_PIXEL,
            row=fila - 1,
            rowOff=desplazamiento_y * EMU_POR_PIXEL,
        ),
        ext=XDRPositiveSize2D(
            cx=int(imagen.width * EMU_POR_PIXEL),
            cy=int(imagen.height * EMU_POR_PIXEL),
        ),
    )
    hoja.add_image(imagen)


def _agregar_fotos(hoja: Worksheet, dia: Dia) -> None:
    filas = {"A": [26], "B": [27, 28], "C": [29], "AD": [30, 31]}
    for espacio, filas_espacio in filas.items():
        fotos = [foto for foto in dia.fotos if foto.espacio == espacio]
        for indice, foto in enumerate(fotos[: len(filas_espacio) * 2]):
            ruta = Path("/data/fotos") / Path(foto.archivo).name
            if ruta.is_file():
                _anclar_foto(hoja, ruta, filas_espacio[indice // 2], bool(indice % 2))


def _llenar_comunes(
    hoja: Worksheet,
    reporte: Reporte,
    dia: Dia,
    colaboradores: list[Colaborador],
    herramientas: list[Herramienta],
) -> None:
    hoja["C6"] = dia.fecha
    hoja["C6"].number_format = "dd/mm/yyyy"
    hoja["I6"] = reporte.semana
    asignaciones = {
        colaborador.id: sorted(
            actividad.letra
            for actividad in dia.actividades
            if any(item.colaborador_id == colaborador.id for item in actividad.asignaciones)
        )
        for colaborador in colaboradores
    }
    for fila, colaborador in enumerate(colaboradores[:13], start=10):
        hoja.cell(fila, 2, texto_seguro(colaborador.nombre))
        hoja.cell(fila, 8, ", ".join(asignaciones[colaborador.id]))
    actividades = {actividad.letra: actividad for actividad in dia.actividades}
    jornada = 5 if dia.dia_semana == 5 else 8
    for columna, letra in enumerate(("A", "B", "C"), start=13):
        hoja.cell(11, columna, f'=COUNTIF($H$10:$H$22,"*"&{get_column_letter(columna)}$10&"*")')
        actividad = actividades.get(letra)
        personas = len(actividad.asignaciones) if actividad else 0
        horas = sum(item.horas for item in actividad.asignaciones) if actividad else 0
        hoja.cell(13, columna, horas / personas if personas else jornada)
    cantidades = {item.herramienta_id: item.cantidad for item in dia.herramientas}
    for fila, herramienta in enumerate(herramientas[:14], start=10):
        hoja.cell(fila, 17, cantidades.get(herramienta.id, 0))
        hoja.cell(fila, 18, texto_seguro(herramienta.nombre))


def _llenar_dia(
    hoja: Worksheet,
    reporte: Reporte,
    dia: Dia,
    colaboradores: list[Colaborador],
    herramientas: list[Herramienta],
) -> None:
    con_actividades = bool(dia.actividades)
    hoja.print_area = "A1:T58" if con_actividades else "A1:T54"
    _llenar_comunes(hoja, reporte, dia, colaboradores, herramientas)
    actividades = {actividad.letra: actividad for actividad in dia.actividades}
    if con_actividades:
        for celda, letra in (("D26", "A"), ("D27", "B"), ("D29", "C")):
            descripcion = actividades[letra].descripcion if letra in actividades else ""
            hoja[celda] = texto_seguro(descripcion)
        hoja["D30"] = texto_seguro(dia.texto_fotos)
        hoja["A52"] = texto_seguro(dia.observacion)
        hoja["F57"] = texto_seguro(reporte.elaborado_por.nombre) if reporte.elaborado_por else ""
        hoja["R57"] = texto_seguro(reporte.revisado_por.nombre) if reporte.revisado_por else ""
        _agregar_fotos(hoja, dia)
    else:
        hoja["A48"] = texto_seguro(dia.observacion)
        hoja["F53"] = texto_seguro(reporte.elaborado_por.nombre) if reporte.elaborado_por else ""
        hoja["R53"] = texto_seguro(reporte.revisado_por.nombre) if reporte.revisado_por else ""
    _anclar_logo(hoja)
    _anclar_mapa(hoja, con_actividades)


def generar_formato(reporte: Reporte) -> bytes:
    session = object_session(reporte)
    if session is None:
        raise RuntimeError("El reporte debe estar asociado a una sesión")
    colaboradores = list(
        session.scalars(
            select(Colaborador)
            .where(Colaborador.activo.is_(True))
            .order_by(Colaborador.orden, Colaborador.id)
        )
    )
    herramientas = list(
        session.scalars(
            select(Herramienta)
            .where(Herramienta.activo.is_(True))
            .order_by(Herramienta.orden, Herramienta.id)
        )
    )
    libro = load_workbook(PLANTILLAS_DIR / "plantilla_formato.xlsx")
    hojas_dias = []
    for dia, nombre in zip(reporte.dias, NOMBRES_DIAS, strict=True):
        base = libro["base_actividades" if dia.actividades else "base_sin_actividades"]
        hoja = libro.copy_worksheet(base)
        hoja.title = nombre
        _llenar_dia(hoja, reporte, dia, colaboradores, herramientas)
        hojas_dias.append(hoja)
    libro.remove(libro["base_actividades"])
    libro.remove(libro["base_sin_actividades"])
    datos = libro["Datos"]
    for columna, nombre in enumerate(NOMBRES_DIAS, start=5):
        letra_columna = get_column_letter(columna)
        datos[f"{letra_columna}8"] = f"=+{nombre}!M19+{nombre}!N19+{nombre}!O19"
        datos[f"{letra_columna}9"] = f"=+{nombre}!M17"
    libro._sheets = [*hojas_dias, datos]
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
