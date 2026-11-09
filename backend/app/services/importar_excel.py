import base64
import binascii
import json
import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

from openpyxl import load_workbook
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import DomainError, InvalidFileError
from app.models import Colaborador, Firmante
from app.schemas.exportar import ReporteExportar
from app.services.fotos import normalizar_foto
from app.services.respaldo_excel import MARCADOR_RESPALDO, VERSION_RESPALDO

NOMBRES_DIAS = ("Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado")
LETRAS = tuple("ABCDEFGHIJ")


@dataclass(frozen=True)
class Importacion:
    datos: ReporteExportar
    contenidos: list[bytes]
    avisos: list[str]
    origen: Literal["respaldo", "formato"]


def _trozos_fila(hoja, fila: int, columna_inicial: int = 1) -> str:
    partes = []
    columna = columna_inicial
    while isinstance(hoja.cell(fila, columna).value, str):
        partes.append(hoja.cell(fila, columna).value)
        columna += 1
    return "".join(partes)


def _texto(valor: object) -> str:
    texto = "" if valor is None else str(valor)
    if texto.startswith("'"):
        texto = texto[1:]
    return texto.strip()


def _nombre_normalizado(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", _texto(valor).casefold())
    return " ".join("".join(letra for letra in texto if not unicodedata.combining(letra)).split())


def _dia(datos: dict, indice: int) -> dict:
    return next(item for item in datos["dias"] if item["dia_semana"] == indice)


def _actividad(dia: dict, letra: str, avisos: list[str], nombre_dia: str) -> dict:
    existente = next((item for item in dia["actividades"] if item["letra"] == letra), None)
    if existente is not None:
        return existente
    nueva = {"letra": letra, "descripcion": "", "asignaciones": []}
    dia["actividades"].append(nueva)
    avisos.append(f"{nombre_dia}: se creó la actividad {letra} sin descripción")
    return nueva


def _truncar(valor: str, maximo: int, avisos: list[str], contexto: str) -> str:
    if len(valor) <= maximo:
        return valor
    avisos.append(f"{contexto}: el texto se truncó a {maximo} caracteres")
    return valor[:maximo]


def _recalcular_asignaciones(dia: dict) -> None:
    settings = get_settings()
    jornada = settings.jornada_sabado if dia["dia_semana"] == 5 else settings.jornada_semana
    ids = {
        asignacion["colaborador_id"]
        for actividad in dia["actividades"]
        for asignacion in actividad["asignaciones"]
    }
    for colaborador_id in ids:
        asignaciones = [
            asignacion
            for actividad in dia["actividades"]
            for asignacion in actividad["asignaciones"]
            if asignacion["colaborador_id"] == colaborador_id
        ]
        manuales = [item for item in asignaciones if item.get("horas_manual", False)]
        automaticas = [item for item in asignaciones if not item.get("horas_manual", False)]
        restante = max(jornada - sum(item.get("horas") or 0 for item in manuales), 0)
        horas = round(restante / len(automaticas), 2) if automaticas else 0
        for asignacion in automaticas:
            asignacion["horas"] = horas
            asignacion["horas_manual"] = False


def _aplicar_letras(
    dia: dict,
    colaborador_id: int,
    valor: str,
    avisos: list[str],
    nombre_dia: str,
) -> None:
    letras = []
    for parte in re.split(r"[\s,]+", valor.upper()):
        if parte in LETRAS and parte not in letras:
            letras.append(parte)
    anteriores = {
        actividad["letra"]: asignacion
        for actividad in dia["actividades"]
        for asignacion in actividad["asignaciones"]
        if asignacion["colaborador_id"] == colaborador_id
    }
    for actividad in dia["actividades"]:
        actividad["asignaciones"] = [
            item
            for item in actividad["asignaciones"]
            if item["colaborador_id"] != colaborador_id or actividad["letra"] in letras
        ]
    for letra in letras:
        actividad = _actividad(dia, letra, avisos, nombre_dia)
        if not any(item["colaborador_id"] == colaborador_id for item in actividad["asignaciones"]):
            actividad["asignaciones"].append(
                anteriores.get(
                    letra,
                    {
                        "colaborador_id": colaborador_id,
                        "horas": None,
                        "horas_manual": False,
                    },
                )
            )
    _recalcular_asignaciones(dia)


def _aplicar_cantidad(
    dia: dict,
    lista: str,
    campo_id: str,
    item_id: int,
    valor: str,
    avisos: list[str],
    contexto: str,
) -> None:
    try:
        cantidad = 0.0 if not valor else float(valor.replace(",", "."))
        if cantidad < 0 or cantidad > 100_000:
            raise ValueError
    except ValueError:
        avisos.append(f"{contexto}: la cantidad editada no es válida; se conservó la anterior")
        return
    elementos = dia[lista]
    existente = next((item for item in elementos if item[campo_id] == item_id), None)
    if cantidad == 0:
        dia[lista] = [item for item in elementos if item[campo_id] != item_id]
    elif existente is not None:
        existente["cantidad"] = cantidad
    else:
        elementos.append({campo_id: item_id, "cantidad": cantidad})


def _superponer_ediciones(libro, datos: dict, mapa: dict, session: Session) -> list[str]:
    avisos: list[str] = []
    colaboradores = {
        _nombre_normalizado(item.nombre): item
        for item in session.scalars(select(Colaborador).order_by(Colaborador.id))
    }
    firmantes = {
        _nombre_normalizado(item.nombre): item
        for item in session.scalars(select(Firmante).order_by(Firmante.id))
    }
    for clave, entrada in mapa.items():
        if not isinstance(entrada, list) or len(entrada) != 2:
            raise InvalidFileError("El respaldo del archivo está dañado")
        referencia, valor_escrito = entrada
        if not isinstance(referencia, str) or "!" not in referencia:
            raise InvalidFileError("El respaldo del archivo está dañado")
        nombre_hoja, coordenada = referencia.rsplit("!", 1)
        if nombre_hoja not in libro.sheetnames:
            raise InvalidFileError("El respaldo del archivo está dañado")
        valor_actual = libro[nombre_hoja][coordenada].value
        actual = _texto(valor_actual)
        anterior = _texto(valor_escrito)
        mismos_numeros = (
            isinstance(valor_actual, (int, float))
            and not isinstance(valor_actual, bool)
            and isinstance(valor_escrito, (int, float))
            and not isinstance(valor_escrito, bool)
            and float(valor_actual) == float(valor_escrito)
        )
        if actual == anterior or mismos_numeros:
            continue
        if clave.startswith("d"):
            partes = clave.split(".")
            try:
                indice_dia = int(partes[0][1:])
                dia = _dia(datos, indice_dia)
                nombre_dia = NOMBRES_DIAS[indice_dia]
            except (ValueError, IndexError, StopIteration) as error:
                raise InvalidFileError("El respaldo del archivo está dañado") from error
            if partes[1:3] == ["texto_fotos"]:
                dia["texto_fotos"] = _truncar(actual, 1000, avisos, nombre_dia)
                avisos.append(f"{nombre_dia}: se tomó el texto de fotos editado")
            elif partes[1:3] == ["observacion"]:
                dia["observacion"] = _truncar(actual, 2000, avisos, nombre_dia)
                avisos.append(f"{nombre_dia}: se tomó la observación editada")
            elif len(partes) == 4 and partes[1] == "act" and partes[3] == "descripcion":
                actividad = _actividad(dia, partes[2], avisos, nombre_dia)
                actividad["descripcion"] = _truncar(actual, 1000, avisos, nombre_dia)
                avisos.append(
                    f"{nombre_dia}: se tomó la descripción editada de la actividad {partes[2]}"
                )
            elif len(partes) == 4 and partes[1] == "colab" and partes[3] == "letras":
                _aplicar_letras(dia, int(partes[2]), actual, avisos, nombre_dia)
                avisos.append(f"{nombre_dia}: se tomó la asignación editada del colaborador")
            elif len(partes) == 4 and partes[1] == "colab" and partes[3] == "nombre":
                original_id = int(partes[2])
                destino = colaboradores.get(_nombre_normalizado(actual))
                if destino is None:
                    avisos.append(
                        f"{nombre_dia}: no se encontró el colaborador «{actual}»; "
                        "se conservó el original"
                    )
                elif destino.id != original_id:
                    for actividad in dia["actividades"]:
                        for asignacion in actividad["asignaciones"]:
                            if asignacion["colaborador_id"] == original_id:
                                asignacion["colaborador_id"] = destino.id
                        unicas = {}
                        for asignacion in actividad["asignaciones"]:
                            unicas[asignacion["colaborador_id"]] = asignacion
                        actividad["asignaciones"] = list(unicas.values())
                    _recalcular_asignaciones(dia)
                    avisos.append(
                        f"{nombre_dia}: se tomó el colaborador editado «{destino.nombre}»"
                    )
            elif len(partes) == 4 and partes[1] in {"herr", "mat"} and partes[3] == "cantidad":
                es_herramienta = partes[1] == "herr"
                _aplicar_cantidad(
                    dia,
                    "herramientas" if es_herramienta else "materiales",
                    "herramienta_id" if es_herramienta else "material_id",
                    int(partes[2]),
                    actual,
                    avisos,
                    nombre_dia,
                )
                avisos.append(f"{nombre_dia}: se tomó la cantidad editada")
        elif clave in {"firma.elaborado", "firma.revisado"}:
            firmante = firmantes.get(_nombre_normalizado(actual)) if actual else None
            campo = "elaborado_por_id" if clave.endswith("elaborado") else "revisado_por_id"
            if actual and firmante is None:
                avisos.append(f"No se encontró el firmante «{actual}»; se conservó el original")
            else:
                datos[campo] = firmante.id if firmante else None
                avisos.append("Se tomó el firmante editado")
    return avisos


def _leer_respaldo(libro, session: Session) -> Importacion:
    hoja = libro["_respaldo"]
    if hoja["A1"].value != MARCADOR_RESPALDO or hoja["B1"].value != VERSION_RESPALDO:
        raise InvalidFileError("El respaldo del archivo está dañado")
    try:
        datos_modelo = ReporteExportar.model_validate_json(_trozos_fila(hoja, 2))
        mapa = json.loads(_trozos_fila(hoja, 3))
        if not isinstance(mapa, dict):
            raise ValueError
        contenidos = []
        for fila in range(4, hoja.max_row + 1):
            if hoja.cell(fila, 1).value != fila - 4:
                raise ValueError
            contenido = base64.b64decode(_trozos_fila(hoja, fila, 2), validate=True)
            normalizar_foto(contenido, get_settings().max_foto_mb)
            contenidos.append(contenido)
        datos = datos_modelo.model_dump(mode="json")
        avisos = _superponer_ediciones(libro, datos, mapa, session)
        return Importacion(
            datos=ReporteExportar.model_validate(datos),
            contenidos=contenidos,
            avisos=avisos,
            origen="respaldo",
        )
    except InvalidFileError:
        raise
    except (ValidationError, ValueError, TypeError, KeyError, binascii.Error, DomainError) as error:
        raise InvalidFileError("El respaldo del archivo está dañado") from error


def leer_excel(contenido: bytes, session: Session) -> Importacion:
    try:
        libro = load_workbook(BytesIO(contenido), read_only=False, data_only=False, keep_vba=False)
    except Exception as error:
        raise InvalidFileError("Archivo de Excel no válido") from error
    if "_respaldo" in libro.sheetnames:
        return _leer_respaldo(libro, session)
    raise InvalidFileError(
        "Este archivo no tiene datos para reabrir; usa un Excel descargado desde la app"
    )
