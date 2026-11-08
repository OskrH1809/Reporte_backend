from copy import copy
from io import BytesIO
from math import ceil
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
from app.models.reportes import LETRAS_ACTIVIDAD
from app.services.calculos import jornada_dia

PLANTILLAS_DIR = Path(__file__).resolve().parents[1] / "plantillas"
FOTOS_DIR = Path("/data/fotos")
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


def _anclar_mapa(hoja: Worksheet, con_actividades: bool, desplazamiento: int = 0) -> None:
    fila = 34 + desplazamiento if con_actividades else 30
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


def _marcador(hoja: Worksheet, columna: int, fila: int, x_px: int, y_px: int) -> AnchorMarker:
    while x_px >= _pixeles_columna(hoja, columna):
        x_px -= _pixeles_columna(hoja, columna)
        columna += 1
    while y_px >= _pixeles_fila(hoja, fila):
        y_px -= _pixeles_fila(hoja, fila)
        fila += 1
    return AnchorMarker(
        col=columna - 1,
        colOff=x_px * EMU_POR_PIXEL,
        row=fila - 1,
        rowOff=y_px * EMU_POR_PIXEL,
    )


def _acomodar_fotos(hoja: Worksheet, rutas: list[Path], fila_inicio: int, fila_fin: int) -> None:
    if not rutas:
        return
    filas, columnas = (1, 1) if len(rutas) == 1 else ((1, 2) if len(rutas) == 2 else (2, 2))
    ancho_area = sum(_pixeles_columna(hoja, indice) for indice in range(14, 21))
    alto_area = sum(_pixeles_fila(hoja, fila) for fila in range(fila_inicio, fila_fin + 1))
    ancho_casilla = ancho_area / columnas
    alto_casilla = alto_area / filas
    margen = 4
    for indice, ruta in enumerate(rutas[:4]):
        imagen = ExcelImage(ruta)
        ancho_disponible = max(1, ancho_casilla - 2 * margen)
        alto_disponible = max(1, alto_casilla - 2 * margen)
        escala = min(ancho_disponible / imagen.width, alto_disponible / imagen.height)
        ancho = max(1, int(imagen.width * escala))
        alto = max(1, int(imagen.height * escala))
        fila_casilla, columna_casilla = divmod(indice, columnas)
        x = int(columna_casilla * ancho_casilla + margen + (ancho_disponible - ancho) / 2)
        y = int(fila_casilla * alto_casilla + margen + (alto_disponible - alto) / 2)
        imagen.width = ancho
        imagen.height = alto
        imagen.anchor = OneCellAnchor(
            _from=_marcador(hoja, 14, fila_inicio, x, y),
            ext=XDRPositiveSize2D(cx=ancho * EMU_POR_PIXEL, cy=alto * EMU_POR_PIXEL),
        )
        hoja.add_image(imagen)


def _agregar_fotos(
    hoja: Worksheet,
    dia: Dia,
    extras: tuple[str, ...],
    desplazamiento_bandas: int,
    desplazamiento: int,
) -> None:
    areas = {
        "A": (26 + desplazamiento_bandas, 26 + desplazamiento_bandas),
        "B": (27 + desplazamiento_bandas, 28 + desplazamiento_bandas),
        "C": (29 + desplazamiento_bandas, 29 + desplazamiento_bandas),
        **{
            letra: (30 + indice + desplazamiento_bandas, 30 + indice + desplazamiento_bandas)
            for indice, letra in enumerate(extras)
        },
        "AD": (30 + desplazamiento, 31 + desplazamiento),
    }
    for espacio, (fila_inicio, fila_fin) in areas.items():
        rutas = [
            FOTOS_DIR / Path(foto.archivo).name
            for foto in dia.fotos
            if foto.espacio == espacio and (FOTOS_DIR / Path(foto.archivo).name).is_file()
        ][:4]
        _acomodar_fotos(hoja, rutas, fila_inicio, fila_fin)


def _insertar_filas(hoja: Worksheet, fila: int, cantidad: int) -> None:
    rangos = [
        (rango.min_col, rango.min_row, rango.max_col, rango.max_row)
        for rango in hoja.merged_cells.ranges
        if rango.min_row >= fila
    ]
    for min_col, min_row, max_col, max_row in rangos:
        hoja.unmerge_cells(
            start_row=min_row, start_column=min_col, end_row=max_row, end_column=max_col
        )
    ultima_fila = hoja.max_row
    hoja.move_range(f"A{fila}:T{ultima_fila}", rows=cantidad, translate=True)
    for min_col, min_row, max_col, max_row in rangos:
        hoja.merge_cells(
            start_row=min_row + cantidad,
            start_column=min_col,
            end_row=max_row + cantidad,
            end_column=max_col,
        )
    for numero in range(ultima_fila, fila - 1, -1):
        hoja.row_dimensions[numero + cantidad].height = hoja.row_dimensions[numero].height
        hoja.row_dimensions[numero + cantidad].hidden = hoja.row_dimensions[numero].hidden
    for numero in range(fila, fila + cantidad):
        hoja.row_dimensions[numero].hidden = False


def _insertar_actividades(
    hoja: Worksheet, actividades: dict[str, object], extras: tuple[str, ...]
) -> None:
    if not extras:
        return
    _insertar_filas(hoja, 30, len(extras))
    for indice, letra in enumerate(extras):
        fila = 30 + indice
        hoja.row_dimensions[fila].height = 253.5
        for columna in range(1, 21):
            hoja.cell(fila, columna)._style = copy(hoja.cell(29, columna)._style)
        hoja.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=3)
        hoja.merge_cells(start_row=fila, start_column=4, end_row=fila, end_column=12)
        hoja.merge_cells(start_row=fila, start_column=14, end_row=fila, end_column=20)
        actividad = actividades.get(letra)
        hoja.cell(fila, 1, 4 + indice)
        hoja.cell(fila, 4, texto_seguro(actividad.descripcion) if actividad else "")
        hoja.cell(fila, 13, letra)
    hoja.cell(30 + len(extras), 1, 4 + len(extras))


def _insertar_bandas(
    hoja: Worksheet, actividades: dict[str, object], extras: tuple[str, ...], jornada: float
) -> list[str]:
    bandas = ceil(len(extras) / 3)
    if not bandas:
        return []
    _insertar_filas(hoja, 24, 5 * bandas)
    totales = []
    filas_modelo = (10, 11, 13, 15, 19)
    for banda in range(bandas):
        fila_inicio = 24 + 5 * banda
        letras = extras[3 * banda : 3 * banda + 3]
        for desplazamiento, fila_modelo in enumerate(filas_modelo):
            fila = fila_inicio + desplazamiento
            hoja.row_dimensions[fila].height = hoja.row_dimensions[fila_modelo].height
            for columna in range(10, 16):
                hoja.cell(fila, columna)._style = copy(hoja.cell(fila_modelo, columna)._style)
        for desplazamiento in range(1, 5):
            hoja.merge_cells(
                start_row=fila_inicio + desplazamiento,
                start_column=10,
                end_row=fila_inicio + desplazamiento,
                end_column=12,
            )
        hoja.cell(fila_inicio + 1, 10, "Número de colaborador en actividad")
        hoja.cell(fila_inicio + 2, 10, "Horas de actividad")
        hoja.cell(fila_inicio + 3, 10, "Horas hombres ")
        hoja.cell(fila_inicio + 4, 10, "Total de actividades")
        for indice, letra in enumerate(letras, start=13):
            columna = get_column_letter(indice)
            actividad = actividades.get(letra)
            personas = len(actividad.asignaciones) if actividad else 0
            horas = sum(item.horas for item in actividad.asignaciones) if actividad else 0
            hoja.cell(fila_inicio, indice, letra)
            hoja.cell(
                fila_inicio + 1,
                indice,
                f'=COUNTIF($H$10:$H$22,"*"&{columna}${fila_inicio}&"*")',
            )
            hoja.cell(fila_inicio + 2, indice, horas / personas if personas else jornada)
            hoja.cell(
                fila_inicio + 3,
                indice,
                f"=+{columna}{fila_inicio + 2}*{columna}{fila_inicio + 1}",
            )
            hoja.cell(
                fila_inicio + 4,
                indice,
                f"=+IF({columna}{fila_inicio + 1}=0,0,1)",
            )
            totales.append(f"{columna}{fila_inicio + 4}")
    return totales


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
    jornada = jornada_dia(dia)
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
) -> list[str]:
    con_actividades = bool(dia.actividades)
    _llenar_comunes(hoja, reporte, dia, colaboradores, herramientas)
    actividades = {actividad.letra: actividad for actividad in dia.actividades}
    if con_actividades:
        indice_mas_alto = max(LETRAS_ACTIVIDAD.index(letra) for letra in actividades)
        extras = LETRAS_ACTIVIDAD[3 : indice_mas_alto + 1]
        bandas = ceil(len(extras) / 3)
        desplazamiento_bandas = 5 * bandas
        desplazamiento = desplazamiento_bandas + len(extras)
        _insertar_actividades(hoja, actividades, extras)
        totales_extras = _insertar_bandas(hoja, actividades, extras, jornada_dia(dia))
        for fila, letra in ((26, "A"), (27, "B"), (29, "C")):
            descripcion = actividades[letra].descripcion if letra in actividades else ""
            hoja.cell(fila + desplazamiento_bandas, 4, texto_seguro(descripcion))
        hoja.cell(30 + desplazamiento, 4, texto_seguro(dia.texto_fotos))
        hoja.cell(52 + desplazamiento, 1, texto_seguro(dia.observacion))
        hoja.cell(
            57 + desplazamiento,
            6,
            texto_seguro(reporte.elaborado_por.nombre) if reporte.elaborado_por else "",
        )
        hoja.cell(
            57 + desplazamiento,
            18,
            texto_seguro(reporte.revisado_por.nombre) if reporte.revisado_por else "",
        )
        formulas_horas = ["M15", "N15", "O15"]
        for banda in range(bandas):
            fila = 24 + 5 * banda
            formulas_horas.extend(
                f"{get_column_letter(13 + indice)}{fila + 3}"
                for indice in range(len(extras[3 * banda : 3 * banda + 3]))
            )
        hoja["M17"] = "=+" + "+".join(formulas_horas)
        hoja.print_area = f"A1:T{58 + desplazamiento}"
        _agregar_fotos(hoja, dia, extras, desplazamiento_bandas, desplazamiento)
        totales = ["M19", "N19", "O19", *totales_extras]
    else:
        hoja.print_area = "A1:T54"
        hoja["A48"] = texto_seguro(dia.observacion)
        hoja["F53"] = texto_seguro(reporte.elaborado_por.nombre) if reporte.elaborado_por else ""
        hoja["R53"] = texto_seguro(reporte.revisado_por.nombre) if reporte.revisado_por else ""
        desplazamiento = 0
        totales = ["M19", "N19", "O19"]
    _anclar_logo(hoja)
    _anclar_mapa(hoja, con_actividades, desplazamiento)
    return totales


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
        totales = _llenar_dia(hoja, reporte, dia, colaboradores, herramientas)
        hojas_dias.append((hoja, totales))
    libro.remove(libro["base_actividades"])
    libro.remove(libro["base_sin_actividades"])
    datos = libro["Datos"]
    for columna, (nombre, (_, totales)) in enumerate(
        zip(NOMBRES_DIAS, hojas_dias, strict=True), start=5
    ):
        letra_columna = get_column_letter(columna)
        datos[f"{letra_columna}8"] = "=+" + "+".join(f"{nombre}!{celda}" for celda in totales)
        datos[f"{letra_columna}9"] = f"=+{nombre}!M17"
    libro._sheets = [*(hoja for hoja, _ in hojas_dias), datos]
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
