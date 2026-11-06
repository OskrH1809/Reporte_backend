from copy import copy
from datetime import date
from io import BytesIO
from math import ceil
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor, XDRPositiveSize2D
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.pagebreak import Break
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import select
from sqlalchemy.orm import object_session

from app.models import Colaborador, Dia, Herramienta, Material, Reporte
from app.services import fotos
from app.services.calculos import jornada_dia, totales_dia
from app.services.excel_formato import EMU_POR_PIXEL, PLANTILLAS_DIR, texto_seguro

VERDE_OSCURO = "176B2C"
VERDE_CLARO = "EAF7ED"
BLANCO = "FFFFFF"
BORDE = Side(style="thin", color="B7C8BA")
NOMBRES_DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado")
FILAS_FOTOS_POR_PAGINA = 3
MARGEN_MAPA_PX = 16
# LibreOffice pinta en la página anterior una imagen anclada al borde de la fila tras un salto.
MARGEN_SUPERIOR_PX = 4
ETIQUETAS_FOTOS = {
    "A": "Actividad A",
    "B": "Actividad B",
    "C": "Actividad C",
    "AD": "Antes y después",
}
Columna = tuple[str, int, int, str]


class Formula(str):
    pass


def _configurar_hoja(hoja: Worksheet) -> None:
    hoja.sheet_view.showGridLines = False
    hoja.page_setup.paperSize = hoja.PAPERSIZE_LETTER
    hoja.page_setup.orientation = hoja.ORIENTATION_PORTRAIT
    hoja.page_setup.fitToWidth = 1
    hoja.page_setup.fitToHeight = 0
    hoja.sheet_properties.pageSetUpPr.fitToPage = True
    hoja.page_margins.left = 0.4
    hoja.page_margins.right = 0.4
    hoja.page_margins.top = 0.4
    hoja.page_margins.bottom = 0.4
    for columna in range(1, 13):
        hoja.column_dimensions[chr(64 + columna)].width = 9.5


def _alto_texto(valores: list[tuple[object, int]]) -> float:
    lineas = 1
    for valor, ancho_columnas in valores:
        if valor is None:
            continue
        caracteres_por_ancho = max(1, int(ancho_columnas * 9.5))
        lineas = max(lineas, ceil(len(str(valor)) / caracteres_por_ancho))
    return max(18, 15 * lineas)


def _valor_celda(celda, valor: object, alineacion: str) -> None:
    if isinstance(valor, Formula):
        celda.value = str(valor)
    elif isinstance(valor, str):
        celda.value = texto_seguro(valor)
    else:
        celda.value = valor
    celda.font = Font(name="Arial", size=10)
    es_numero = isinstance(valor, (int, float)) and not isinstance(valor, bool)
    celda.alignment = Alignment(
        horizontal="right" if es_numero else alineacion,
        vertical="top",
        wrap_text=True,
    )
    if isinstance(valor, date):
        celda.number_format = "dd/mm/yyyy"
    elif es_numero:
        celda.number_format = "0.##"


def _tabla(hoja: Worksheet, fila: int, columnas: list[Columna], filas: list[list[object]]) -> int:
    for encabezado, col_ini, col_fin, alineacion in columnas:
        if col_ini != col_fin:
            hoja.merge_cells(start_row=fila, start_column=col_ini, end_row=fila, end_column=col_fin)
        celda = hoja.cell(fila, col_ini, texto_seguro(encabezado))
        celda.font = Font(name="Arial", bold=True, color=BLANCO)
        celda.fill = PatternFill("solid", fgColor=VERDE_OSCURO)
        celda.border = Border(bottom=BORDE)
        celda.alignment = Alignment(horizontal=alineacion, vertical="center", wrap_text=True)
    hoja.row_dimensions[fila].height = _alto_texto(
        [(encabezado, col_fin - col_ini + 1) for encabezado, col_ini, col_fin, _ in columnas]
    )
    for desplazamiento, valores in enumerate(filas, start=1):
        fila_actual = fila + desplazamiento
        for valor, (_encabezado, col_ini, col_fin, alineacion) in zip(
            valores, columnas, strict=True
        ):
            if col_ini != col_fin:
                hoja.merge_cells(
                    start_row=fila_actual,
                    start_column=col_ini,
                    end_row=fila_actual,
                    end_column=col_fin,
                )
            celda = hoja.cell(fila_actual, col_ini)
            _valor_celda(celda, valor, alineacion)
            celda.fill = PatternFill(
                "solid", fgColor=VERDE_CLARO if desplazamiento % 2 == 0 else BLANCO
            )
            celda.border = Border(bottom=BORDE)
        hoja.row_dimensions[fila_actual].height = _alto_texto(
            [
                (valor, col_fin - col_ini + 1)
                for valor, (_encabezado, col_ini, col_fin, _alineacion) in zip(
                    valores, columnas, strict=True
                )
            ]
        )
    return fila + len(filas) + 2


def _anclar_imagen(
    hoja: Worksheet,
    ruta: Path,
    fila: int,
    columna: int,
    ancho_maximo: int,
    alto_maximo: int,
    ancho_recuadro: int,
) -> None:
    imagen = ExcelImage(ruta)
    escala = min(ancho_maximo / imagen.width, alto_maximo / imagen.height)
    imagen.width = max(1, round(imagen.width * escala))
    imagen.height = max(1, round(imagen.height * escala))
    desplazamiento_x = max(0, (ancho_recuadro - imagen.width) // 2)
    desplazamiento_y = max(0, (alto_maximo - imagen.height) // 2)
    imagen.anchor = OneCellAnchor(
        _from=AnchorMarker(
            col=columna,
            colOff=desplazamiento_x * EMU_POR_PIXEL,
            row=fila - 1,
            rowOff=(desplazamiento_y + MARGEN_SUPERIOR_PX) * EMU_POR_PIXEL,
        ),
        ext=XDRPositiveSize2D(
            cx=imagen.width * EMU_POR_PIXEL,
            cy=imagen.height * EMU_POR_PIXEL,
        ),
    )
    hoja.add_image(imagen)


def _encabezado(hoja: Worksheet, titulo: str, subtitulo: str) -> int:
    for fila in range(1, 4):
        hoja.row_dimensions[fila].height = 18
    _anclar_imagen(hoja, PLANTILLAS_DIR / "logo.png", 1, 0, 125, 53, 125)
    hoja.merge_cells("D1:L2")
    celda = hoja["D1"]
    celda.value = texto_seguro(titulo)
    celda.font = Font(name="Arial", size=16, bold=True, color=VERDE_OSCURO)
    celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    hoja.merge_cells("D3:L3")
    hoja["D3"] = texto_seguro(subtitulo)
    hoja["D3"].font = Font(name="Arial", size=10)
    hoja["D3"].alignment = Alignment(horizontal="center")
    return 5


def _tarjetas(hoja: Worksheet, fila: int, indicadores: list[tuple[str, object]]) -> int:
    for indice, (etiqueta, valor) in enumerate(indicadores):
        inicio = indice * 3 + 1
        fin = inicio + 2
        hoja.merge_cells(start_row=fila, start_column=inicio, end_row=fila, end_column=fin)
        hoja.merge_cells(start_row=fila + 1, start_column=inicio, end_row=fila + 1, end_column=fin)
        etiqueta_celda = hoja.cell(fila, inicio, texto_seguro(etiqueta))
        etiqueta_celda.font = Font(name="Arial", bold=True, color=VERDE_OSCURO)
        etiqueta_celda.alignment = Alignment(horizontal="center")
        valor_celda = hoja.cell(fila + 1, inicio)
        _valor_celda(valor_celda, valor, "center")
        valor_celda.font = Font(name="Arial", size=16, bold=True, color=VERDE_OSCURO)
        valor_celda.alignment = Alignment(horizontal="center")
        for fila_tarjeta in (fila, fila + 1):
            for columna in range(inicio, fin + 1):
                hoja.cell(fila_tarjeta, columna).fill = PatternFill("solid", fgColor=VERDE_CLARO)
    hoja.row_dimensions[fila].height = 18
    hoja.row_dimensions[fila + 1].height = 24
    return fila + 3


def _totales_reporte(reporte: Reporte) -> list[tuple[int, float, int, list[str]]]:
    return [totales_dia(dia, jornada_dia(dia)) for dia in reporte.dias]


def _resumen(
    libro: Workbook,
    reporte: Reporte,
    colaboradores: list[Colaborador],
    herramientas: list[Herramienta],
    materiales: list[Material],
) -> None:
    hoja = libro.active
    hoja.title = "Resumen"
    _configurar_hoja(hoja)
    fila = _encabezado(
        hoja,
        "Reporte semanal de servicios generales",
        (
            f"Semana {reporte.semana} de {reporte.anio} · "
            f"{reporte.dias[0].fecha:%d/%m/%Y}–{reporte.dias[-1].fecha:%d/%m/%Y}"
        ),
    )
    totales = _totales_reporte(reporte)
    fila = _tarjetas(
        hoja,
        fila,
        [
            ("Horas-hombre", sum(total[1] for total in totales)),
            ("Actividades", sum(total[2] for total in totales)),
            ("Días trabajados", sum(1 for total in totales if total[2])),
            (
                "Personas",
                len(
                    {
                        asignacion.colaborador_id
                        for dia in reporte.dias
                        for actividad in dia.actividades
                        for asignacion in actividad.asignaciones
                    }
                ),
            ),
        ],
    )
    inicio_dias = fila + 1
    filas_dias = [
        [
            nombre,
            dia.fecha,
            total[2],
            total[0],
            total[1],
            dia.observacion if not dia.actividades else "",
        ]
        for dia, nombre, total in zip(reporte.dias, NOMBRES_DIAS, totales, strict=True)
    ]
    filas_dias.append(
        [
            "Total",
            "",
            Formula(f"=SUM(E{inicio_dias}:E{inicio_dias + 5})"),
            "",
            Formula(f"=SUM(I{inicio_dias}:I{inicio_dias + 5})"),
            "",
        ]
    )
    fila = _tabla(
        hoja,
        fila,
        [
            ("Día", 1, 2, "left"),
            ("Fecha", 3, 4, "left"),
            ("Actividades", 5, 6, "right"),
            ("Personas", 7, 8, "right"),
            ("Horas-hombre", 9, 10, "right"),
            ("Observación", 11, 12, "left"),
        ],
        filas_dias,
    )
    filas_colaboradores: list[list[object]] = []
    for colaborador in colaboradores:
        horas_dias = [
            sum(
                asignacion.horas
                for actividad in dia.actividades
                for asignacion in actividad.asignaciones
                if asignacion.colaborador_id == colaborador.id
            )
            for dia in reporte.dias
        ]
        if any(horas_dias):
            fila_excel = fila + len(filas_colaboradores) + 1
            filas_colaboradores.append(
                [colaborador.nombre, *horas_dias, Formula(f"=SUM(D{fila_excel}:I{fila_excel})")]
            )
    inicio_colaboradores = fila + 1
    if filas_colaboradores:
        fin_colaboradores = inicio_colaboradores + len(filas_colaboradores) - 1
        filas_colaboradores.append(
            [
                "Total",
                *[
                    Formula(f"=SUM({col}{inicio_colaboradores}:{col}{fin_colaboradores})")
                    for col in "DEFGHI"
                ],
                Formula(f"=SUM(J{inicio_colaboradores}:J{fin_colaboradores})"),
            ]
        )
    fila = _tabla(
        hoja,
        fila,
        [
            ("Colaborador", 1, 3, "left"),
            *[
                (nombre[:3], indice, indice, "right")
                for indice, nombre in enumerate(NOMBRES_DIAS, 4)
            ],
            ("Total", 10, 12, "right"),
        ],
        filas_colaboradores,
    )
    cantidades_herramientas = {
        item.id: sum(
            cantidad.cantidad
            for dia in reporte.dias
            for cantidad in dia.herramientas
            if cantidad.herramienta_id == item.id
        )
        for item in herramientas
    }
    fila = _tabla(
        hoja,
        fila,
        [("Herramienta", 1, 8, "left"), ("Cantidad total", 9, 12, "right")],
        [
            [item.nombre, cantidades_herramientas[item.id]]
            for item in herramientas
            if cantidades_herramientas[item.id]
        ],
    )
    cantidades_materiales = {
        item.id: sum(
            cantidad.cantidad
            for dia in reporte.dias
            for cantidad in dia.materiales
            if cantidad.material_id == item.id
        )
        for item in materiales
    }
    _tabla(
        hoja,
        fila,
        [
            ("Material", 1, 6, "left"),
            ("Unidad", 7, 9, "left"),
            ("Cantidad total", 10, 12, "right"),
        ],
        [
            [item.nombre, item.unidad, cantidades_materiales[item.id]]
            for item in materiales
            if cantidades_materiales[item.id]
        ],
    )
    _finalizar_hoja(hoja)


def _seccion_fotos(hoja: Worksheet, dia: Dia, fila: int) -> int:
    fotos_existentes = [
        foto
        for espacio in ("A", "B", "C", "AD")
        for foto in dia.fotos
        if foto.espacio == espacio and (fotos.FOTOS_DIR / Path(foto.archivo).name).is_file()
    ]
    if not fotos_existentes:
        return fila
    hoja.row_breaks.append(Break(id=fila - 1))
    hoja.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=12)
    hoja.cell(fila, 1, "Evidencia fotográfica").font = Font(
        name="Arial", size=14, bold=True, color=VERDE_OSCURO
    )
    hoja.row_dimensions[fila].height = 24
    fila += 1
    filas_fotos = 0
    for espacio in ("A", "B", "C", "AD"):
        grupo = [foto for foto in fotos_existentes if foto.espacio == espacio]
        if not grupo:
            continue
        # El salto va antes del título para que nunca quede separado de sus fotos.
        if filas_fotos and filas_fotos % FILAS_FOTOS_POR_PAGINA == 0:
            hoja.row_breaks.append(Break(id=fila - 1))
        hoja.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=12)
        hoja.cell(fila, 1, ETIQUETAS_FOTOS[espacio]).font = Font(
            name="Arial", bold=True, color=VERDE_OSCURO
        )
        hoja.row_dimensions[fila].height = 18
        fila += 1
        for indice in range(0, len(grupo), 2):
            if indice and filas_fotos % FILAS_FOTOS_POR_PAGINA == 0:
                hoja.row_breaks.append(Break(id=fila - 1))
            hoja.row_dimensions[fila].height = 195
            for posicion, foto in enumerate(grupo[indice : indice + 2]):
                _anclar_imagen(
                    hoja,
                    fotos.FOTOS_DIR / Path(foto.archivo).name,
                    fila,
                    0 if posicion == 0 else 6,
                    340,
                    255,
                    340,
                )
            filas_fotos += 1
            fila += 1
    return fila + 1


def _mapa_observacion_firmas(hoja: Worksheet, reporte: Reporte, dia: Dia, fila: int) -> int:
    hoja.row_breaks.append(Break(id=fila - 1))
    mapa = ExcelImage(PLANTILLAS_DIR / "mapa.png")
    alto_mapa = round(420 * mapa.height / mapa.width)
    hoja.row_dimensions[fila].height = (alto_mapa + MARGEN_MAPA_PX) * 72 / 96
    _anclar_imagen(hoja, PLANTILLAS_DIR / "mapa.png", fila, 0, 420, alto_mapa, 850)
    fila += 1
    fila = _tabla(
        hoja,
        fila,
        [("Observación", 1, 12, "left")],
        [[dia.observacion]],
    )
    _tabla(
        hoja,
        fila,
        [("Elabora", 1, 6, "left"), ("Revisa", 7, 12, "left")],
        [
            [
                reporte.elaborado_por.nombre if reporte.elaborado_por else "",
                reporte.revisado_por.nombre if reporte.revisado_por else "",
            ]
        ],
    )
    return fila + 2


def _hoja_dia(libro: Workbook, reporte: Reporte, dia: Dia, nombre: str) -> None:
    hoja = libro.create_sheet(nombre)
    _configurar_hoja(hoja)
    fila = _encabezado(hoja, nombre, f"{dia.fecha:%d/%m/%Y}")
    fila = _tabla(
        hoja,
        fila,
        [
            ("Actividad", 1, 1, "left"),
            ("Descripción", 2, 9, "left"),
            ("Personas", 10, 10, "right"),
            ("Horas-hombre", 11, 12, "right"),
        ],
        [
            [
                actividad.letra,
                actividad.descripcion,
                len(actividad.asignaciones),
                sum(item.horas for item in actividad.asignaciones),
            ]
            for actividad in dia.actividades
        ],
    )
    fila = _tabla(
        hoja,
        fila,
        [
            ("Colaborador", 1, 6, "left"),
            ("Actividad", 7, 8, "left"),
            ("Horas", 9, 12, "right"),
        ],
        [
            [asignacion.colaborador.nombre, actividad.letra, asignacion.horas]
            for actividad in dia.actividades
            for asignacion in actividad.asignaciones
        ],
    )
    fila = _tabla(
        hoja,
        fila,
        [("Herramienta", 1, 8, "left"), ("Cantidad", 9, 12, "right")],
        [[item.herramienta.nombre, item.cantidad] for item in dia.herramientas if item.cantidad],
    )
    fila = _tabla(
        hoja,
        fila,
        [
            ("Material", 1, 6, "left"),
            ("Unidad", 7, 9, "left"),
            ("Cantidad", 10, 12, "right"),
        ],
        [
            [item.material.nombre, item.material.unidad, item.cantidad]
            for item in dia.materiales
            if item.cantidad
        ],
    )
    if dia.texto_fotos:
        fila = _tabla(
            hoja,
            fila,
            [("Descripción de evidencia", 1, 12, "left")],
            [[dia.texto_fotos]],
        )
    fila = _seccion_fotos(hoja, dia, fila)
    _mapa_observacion_firmas(hoja, reporte, dia, fila)
    _finalizar_hoja(hoja)


def _finalizar_hoja(hoja: Worksheet) -> None:
    for fila in range(1, hoja.max_row + 1):
        if hoja.row_dimensions[fila].height is None:
            valores = [(celda.value, 1) for celda in hoja[fila] if celda.value is not None]
            hoja.row_dimensions[fila].height = _alto_texto(valores)
        for celda in hoja[fila]:
            if celda.value is not None:
                fuente = copy(celda.font)
                fuente.name = "Arial"
                celda.font = fuente
    hoja.print_area = f"A1:L{hoja.max_row}"


def generar_mejorado(reporte: Reporte) -> bytes:
    session = object_session(reporte)
    if session is None:
        raise RuntimeError("El reporte debe estar asociado a una sesión")
    colaboradores = list(session.scalars(select(Colaborador).order_by(Colaborador.orden)))
    herramientas = list(session.scalars(select(Herramienta).order_by(Herramienta.orden)))
    materiales = list(session.scalars(select(Material).order_by(Material.orden)))
    libro = Workbook()
    _resumen(libro, reporte, colaboradores, herramientas, materiales)
    for dia, nombre in zip(reporte.dias, NOMBRES_DIAS, strict=True):
        if dia.actividades:
            _hoja_dia(libro, reporte, dia, nombre)
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
