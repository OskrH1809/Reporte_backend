import base64
import json
from dataclasses import dataclass

from openpyxl.workbook.workbook import Workbook

from app.schemas.exportar import ReporteExportar

MARCADOR_RESPALDO = "RSG-RESPALDO"
VERSION_RESPALDO = 1
TAMANO_TROZO = 30_000
MapaCeldas = dict[str, tuple[str, object]]


@dataclass(frozen=True)
class RespaldoSemana:
    datos: ReporteExportar
    contenidos: list[bytes]


def registrar_celda(
    mapa: MapaCeldas,
    clave: str,
    hoja: str,
    celda: str,
    valor: object,
    *,
    reemplazar: bool = True,
) -> None:
    if reemplazar or clave not in mapa:
        mapa[clave] = (f"{hoja}!{celda}", valor)


def _escribir_trozos(hoja, fila: int, contenido: str, columna_inicial: int = 1) -> None:
    for indice, inicio in enumerate(range(0, len(contenido), TAMANO_TROZO)):
        hoja.cell(fila, columna_inicial + indice, contenido[inicio : inicio + TAMANO_TROZO])


def escribir_respaldo(libro: Workbook, respaldo: RespaldoSemana, mapa: MapaCeldas) -> None:
    hoja = libro.create_sheet("_respaldo")
    hoja["A1"] = MARCADOR_RESPALDO
    hoja["B1"] = VERSION_RESPALDO
    _escribir_trozos(hoja, 2, respaldo.datos.model_dump_json())
    _escribir_trozos(
        hoja,
        3,
        json.dumps(mapa, ensure_ascii=False, separators=(",", ":")),
    )
    for indice, contenido in enumerate(respaldo.contenidos):
        fila = indice + 4
        hoja.cell(fila, 1, indice)
        _escribir_trozos(hoja, fila, base64.b64encode(contenido).decode("ascii"), 2)
    hoja.sheet_state = "veryHidden"
