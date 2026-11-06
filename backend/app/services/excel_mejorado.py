from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import select
from sqlalchemy.orm import object_session

from app.models import Colaborador, Dia, Herramienta, Material, Reporte
from app.services.calculos import totales_dia
from app.services.excel_formato import PLANTILLAS_DIR, texto_seguro

VERDE = "2DB34A"
VERDE_OSCURO = "176B2C"
VERDE_CLARO = "EAF7ED"
BLANCO = "FFFFFF"
BORDE = Side(style="thin", color="B7C8BA")
NOMBRES_DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado")


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
    for columna in range(1, 8):
        hoja.column_dimensions[get_column_letter(columna)].width = 16


def _titulo(hoja: Worksheet, texto: str, fila: int) -> int:
    hoja.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=7)
    celda = hoja.cell(fila, 1, texto_seguro(texto))
    celda.font = Font(name="Arial", size=16, bold=True, color=VERDE_OSCURO)
    celda.alignment = Alignment(horizontal="center")
    return fila + 2


def _tabla(hoja: Worksheet, fila: int, encabezados: list[str], filas: list[list[object]]) -> int:
    for columna, encabezado in enumerate(encabezados, start=1):
        celda = hoja.cell(fila, columna, texto_seguro(encabezado))
        celda.font = Font(name="Arial", bold=True, color=BLANCO)
        celda.fill = PatternFill("solid", fgColor=VERDE_OSCURO)
        celda.border = Border(bottom=BORDE)
        celda.alignment = Alignment(wrap_text=True)
    for desplazamiento, valores in enumerate(filas, start=1):
        for columna, valor in enumerate(valores, start=1):
            celda = hoja.cell(fila + desplazamiento, columna)
            celda.value = texto_seguro(valor) if isinstance(valor, str) else valor
            celda.font = Font(name="Arial", size=10)
            celda.fill = PatternFill(
                "solid", fgColor=VERDE_CLARO if desplazamiento % 2 == 0 else BLANCO
            )
            celda.border = Border(bottom=BORDE)
            celda.alignment = Alignment(vertical="top", wrap_text=True)
    return fila + len(filas) + 2


def _logo(hoja: Worksheet) -> None:
    logo = ExcelImage(PLANTILLAS_DIR / "logo.png")
    logo.width = 125
    logo.height = 55
    hoja.add_image(logo, "A1")


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
    _logo(hoja)
    fila = _titulo(hoja, "Reporte semanal de servicios generales", 1)
    hoja.cell(fila, 1, f"Semana {reporte.semana} de {reporte.anio}")
    rango_fechas = f"Del {reporte.dias[0].fecha:%d/%m/%Y} al {reporte.dias[-1].fecha:%d/%m/%Y}"
    hoja.cell(fila + 1, 1, rango_fechas)
    fila += 3
    totales = [totales_dia(dia, 5 if dia.dia_semana == 5 else 8) for dia in reporte.dias]
    indicadores = [
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
    ]
    for indice, (etiqueta, valor) in enumerate(indicadores, start=1):
        celda = hoja.cell(fila, indice * 2 - 1, etiqueta)
        celda.font = Font(name="Arial", bold=True, color=VERDE_OSCURO)
        hoja.cell(fila + 1, indice * 2 - 1, valor).font = Font(name="Arial", size=16, bold=True)
    fila += 3
    filas_dias = []
    for dia, nombre, total in zip(reporte.dias, NOMBRES_DIAS, totales, strict=True):
        detalle = dia.observacion if not dia.actividades else ""
        filas_dias.append([nombre, dia.fecha, total[2], total[0], total[1], detalle])
    fila = _tabla(
        hoja,
        fila,
        ["Día", "Fecha", "Actividades", "Personas", "Horas-hombre", "Observación"],
        filas_dias,
    )
    filas_colaboradores = []
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
                [colaborador.nombre, *horas_dias, f"=SUM(B{fila_excel}:G{fila_excel})"]
            )
    fila = _tabla(hoja, fila, ["Colaborador", *NOMBRES_DIAS, "Total"], filas_colaboradores)
    cantidades_herramientas = {
        herramienta.id: sum(
            cantidad.cantidad
            for dia in reporte.dias
            for cantidad in dia.herramientas
            if cantidad.herramienta_id == herramienta.id
        )
        for herramienta in herramientas
    }
    fila = _tabla(
        hoja,
        fila,
        ["Herramienta", "Cantidad total"],
        [
            [item.nombre, cantidades_herramientas[item.id]]
            for item in herramientas
            if cantidades_herramientas[item.id]
        ],
    )
    cantidades_materiales = {
        material.id: sum(
            cantidad.cantidad
            for dia in reporte.dias
            for cantidad in dia.materiales
            if cantidad.material_id == material.id
        )
        for material in materiales
    }
    _tabla(
        hoja,
        fila,
        ["Material", "Unidad", "Cantidad total"],
        [
            [item.nombre, item.unidad, cantidades_materiales[item.id]]
            for item in materiales
            if cantidades_materiales[item.id]
        ],
    )


def _fotos(hoja: Worksheet, dia: Dia, fila: int) -> int:
    etiquetas = {
        "A": "Actividad A",
        "B": "Actividad B",
        "C": "Actividad C",
        "AD": "Antes y después",
    }
    for espacio in ("A", "B", "C", "AD"):
        fotos = [item for item in dia.fotos if item.espacio == espacio]
        if not fotos:
            continue
        hoja.cell(fila, 1, etiquetas[espacio]).font = Font(
            name="Arial", bold=True, color=VERDE_OSCURO
        )
        fila += 1
        for indice, foto in enumerate(fotos):
            ruta = Path("/data/fotos") / Path(foto.archivo).name
            if ruta.is_file():
                imagen = ExcelImage(ruta)
                imagen.width = 280
                imagen.height = 180
                columna = "A" if indice % 2 == 0 else "D"
                hoja.add_image(imagen, f"{columna}{fila + (indice // 2) * 10}")
        fila += ((len(fotos) + 1) // 2) * 10
    return fila


def _hoja_dia(libro: Workbook, reporte: Reporte, dia: Dia, nombre: str) -> None:
    hoja = libro.create_sheet(nombre)
    _configurar_hoja(hoja)
    _logo(hoja)
    fila = _titulo(hoja, f"{nombre} · {dia.fecha:%d/%m/%Y}", 1)
    filas_actividades = [
        [
            actividad.letra,
            actividad.descripcion,
            len(actividad.asignaciones),
            sum(item.horas for item in actividad.asignaciones),
        ]
        for actividad in dia.actividades
    ]
    fila = _tabla(
        hoja, fila, ["Actividad", "Descripción", "Personas", "Horas-hombre"], filas_actividades
    )
    filas_personas = [
        [asignacion.colaborador.nombre, actividad.letra, asignacion.horas]
        for actividad in dia.actividades
        for asignacion in actividad.asignaciones
    ]
    fila = _tabla(hoja, fila, ["Colaborador", "Actividad", "Horas"], filas_personas)
    fila = _tabla(
        hoja,
        fila,
        ["Herramienta", "Cantidad"],
        [[item.herramienta.nombre, item.cantidad] for item in dia.herramientas if item.cantidad],
    )
    fila = _tabla(
        hoja,
        fila,
        ["Material", "Unidad", "Cantidad"],
        [
            [item.material.nombre, item.material.unidad, item.cantidad]
            for item in dia.materiales
            if item.cantidad
        ],
    )
    fila = _fotos(hoja, dia, fila)
    mapa = ExcelImage(PLANTILLAS_DIR / "mapa.png")
    mapa.width = 600
    mapa.height = 230
    hoja.add_image(mapa, f"A{fila}")
    fila += 14
    fila = _tabla(hoja, fila, ["Observación"], [[dia.observacion]])
    hoja.cell(fila, 1, f"Elabora: {reporte.elaborado_por.nombre if reporte.elaborado_por else ''}")
    hoja.cell(fila, 5, f"Revisa: {reporte.revisado_por.nombre if reporte.revisado_por else ''}")
    hoja.print_area = f"A1:G{fila + 2}"


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
