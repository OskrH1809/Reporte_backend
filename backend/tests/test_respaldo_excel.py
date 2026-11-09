import base64
import json
from io import BytesIO

from openpyxl import load_workbook
from PIL import Image
from sqlalchemy.orm import Session

from app.models import Colaborador, Herramienta, Material
from app.schemas.exportar import ReporteExportar
from app.services.excel_formato import generar_formato
from app.services.excel_mejorado import generar_mejorado
from app.services.reporte_memoria import armar_reporte
from app.services.respaldo_excel import RespaldoSemana, escribir_respaldo


def _foto(color: str) -> bytes:
    salida = BytesIO()
    Image.new("RGB", (32, 24), color).save(salida, "JPEG")
    return salida.getvalue()


def _datos(colaborador_id: int) -> ReporteExportar:
    return ReporteExportar.model_validate(
        {
            "anio": 2026,
            "semana": 45,
            "dias": [
                {
                    "dia_semana": dia,
                    "observacion": "Observación",
                    "texto_fotos": "Antes y después",
                    "actividades": [
                        {
                            "letra": letra,
                            "descripcion": f"Descripción {letra}",
                            "asignaciones": [{"colaborador_id": colaborador_id}],
                        }
                        for letra in "ABCD"
                    ]
                    if dia == 0
                    else [],
                    "herramientas": [],
                    "materiales": [],
                    "fotos": [
                        {"indice": indice, "espacio": espacio}
                        for indice, espacio in enumerate(("A", "D", "AD"))
                    ]
                    if dia == 0
                    else [],
                }
                for dia in range(6)
            ],
        }
    )


def _reconstruir_fila(hoja, fila: int, inicio: int = 1) -> str:
    partes = []
    columna = inicio
    while hoja.cell(fila, columna).value is not None:
        partes.append(hoja.cell(fila, columna).value)
        columna += 1
    return "".join(partes)


def test_formato_incluye_respaldo_mapa_y_fotos(session: Session) -> None:
    colaborador = Colaborador(nombre="Persona sintética", orden=950)
    session.add(colaborador)
    session.flush()
    datos = _datos(colaborador.id)
    contenidos = [_foto(color) for color in ("red", "green", "blue")]
    reporte = armar_reporte(datos, contenidos, session)

    contenido = generar_formato(
        reporte,
        [colaborador],
        [],
        RespaldoSemana(datos=datos, contenidos=contenidos),
    )
    libro = load_workbook(BytesIO(contenido), data_only=False)
    respaldo = libro["_respaldo"]

    assert respaldo.sheet_state == "veryHidden"
    assert libro.sheetnames[-1] == "_respaldo"
    assert json.loads(_reconstruir_fila(respaldo, 2)) == datos.model_dump(mode="json")
    mapa = json.loads(_reconstruir_fila(respaldo, 3))
    assert mapa["d0.act.D.descripcion"][0] == "Lunes!D35"
    assert [
        base64.b64decode(_reconstruir_fila(respaldo, fila, 2), validate=True)
        for fila in range(4, 7)
    ] == contenidos
    assert libro.sheetnames[:-1] == [
        "Lunes",
        "Martes",
        "Miercoles",
        "Jueves",
        "Viernes",
        "Sabado",
        "Datos",
    ]


def test_mejorado_incluye_respaldo_despues_de_hojas_visibles(session: Session) -> None:
    colaborador = Colaborador(nombre="Persona mejorado", orden=951)
    herramienta = Herramienta(nombre="Herramienta sintética", orden=951)
    material = Material(nombre="Material sintético", unidad="u", orden=951)
    session.add_all([colaborador, herramienta, material])
    session.flush()
    datos = _datos(colaborador.id)
    contenidos = [_foto(color) for color in ("red", "green", "blue")]
    reporte = armar_reporte(datos, contenidos, session)

    contenido = generar_mejorado(
        reporte,
        [colaborador],
        [herramienta],
        [material],
        RespaldoSemana(datos=datos, contenidos=contenidos),
    )
    libro = load_workbook(BytesIO(contenido), data_only=False)

    assert libro.sheetnames[-1] == "_respaldo"
    assert libro["_respaldo"].sheet_state == "veryHidden"
    assert json.loads(_reconstruir_fila(libro["_respaldo"], 2)) == datos.model_dump(mode="json")


def test_respaldo_parte_y_reconstruye_valor_de_setenta_mil_caracteres() -> None:
    from openpyxl import Workbook

    datos = ReporteExportar.model_validate(
        {
            "anio": 2026,
            "semana": 45,
            "dias": [{"dia_semana": dia} for dia in range(6)],
        }
    )
    libro = Workbook()
    texto = "x" * 70_000
    escribir_respaldo(
        libro,
        RespaldoSemana(datos=datos, contenidos=[]),
        {"d0.act.A.descripcion": ("Lunes!D26", texto)},
    )

    mapa = json.loads(_reconstruir_fila(libro["_respaldo"], 3))
    assert mapa["d0.act.A.descripcion"][1] == texto
    assert libro["_respaldo"].cell(3, 3).value is not None
