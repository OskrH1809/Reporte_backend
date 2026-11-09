from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.errors import FileTooLargeError
from app.routers.reportes import obtener_reporte
from app.schemas.exportar import ReporteExportar
from app.services import fotos
from app.services.excel_formato import generar_formato
from app.services.excel_mejorado import generar_mejorado
from app.services.pdf import generar_pdf
from app.services.reporte_memoria import armar_reporte, catalogos_exportacion, desde_orm
from app.services.respaldo_excel import RespaldoSemana

DatabaseSession = Annotated[Session, Depends(get_db)]
router_guardado = APIRouter(prefix="/api/reportes", tags=["exportacion"])
router_memoria = APIRouter(prefix="/api/exportar", tags=["exportacion"])


def _respuesta(contenido: bytes, nombre: str, media_type: str) -> Response:
    return Response(
        content=contenido,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router_guardado.get("/{reporte_id}/exportar/{tipo}", response_model=None)
def exportar(
    reporte_id: int,
    tipo: Literal["formato", "mejorado", "pdf"],
    session: DatabaseSession,
) -> Response:
    reporte = obtener_reporte(session, reporte_id)
    reporte_memoria = desde_orm(reporte)
    codigo = f"CH-RSG-{reporte.semana}-{reporte.anio}"
    if tipo == "formato":
        colaboradores, herramientas, _materiales = catalogos_exportacion(session, solo_activos=True)
        return _respuesta(
            generar_formato(reporte_memoria, colaboradores, herramientas),
            f"{codigo}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    colaboradores, herramientas, materiales = catalogos_exportacion(session, solo_activos=False)
    mejorado = generar_mejorado(reporte_memoria, colaboradores, herramientas, materiales)
    if tipo == "mejorado":
        return _respuesta(
            mejorado,
            f"{codigo}_mejorado.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    return _respuesta(generar_pdf(mejorado), f"{codigo}_mejorado.pdf", "application/pdf")


@router_memoria.post("/{tipo}", response_model=None)
def exportar_memoria(
    tipo: Literal["formato", "mejorado", "pdf"],
    session: DatabaseSession,
    request: Request,
    datos: Annotated[str, Form()],
    archivos: Annotated[list[UploadFile] | None, File(alias="fotos")] = None,
) -> Response:
    try:
        entrada = ReporteExportar.model_validate_json(datos)
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error
    settings: Settings = request.app.state.settings
    contenidos = []
    total = 0
    for archivo in archivos or []:
        contenido = archivo.file.read(settings.max_foto_mb * 1024 * 1024 + 1)
        total += len(contenido)
        if total > settings.max_exportacion_mb * 1024 * 1024:
            raise FileTooLargeError(
                f"La exportación supera el máximo de {settings.max_exportacion_mb} MB"
            )
        contenidos.append(fotos.normalizar_foto(contenido, settings.max_foto_mb))
    reporte = armar_reporte(entrada, contenidos, session)
    respaldo = RespaldoSemana(datos=entrada, contenidos=contenidos)
    codigo = f"CH-RSG-{reporte.semana}-{reporte.anio}"
    if tipo == "formato":
        colaboradores, herramientas, _materiales = catalogos_exportacion(session, solo_activos=True)
        return _respuesta(
            generar_formato(reporte, colaboradores, herramientas, respaldo),
            f"{codigo}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    colaboradores, herramientas, materiales = catalogos_exportacion(session, solo_activos=False)
    mejorado = generar_mejorado(
        reporte,
        colaboradores,
        herramientas,
        materiales,
        respaldo if tipo == "mejorado" else None,
    )
    if tipo == "mejorado":
        return _respuesta(
            mejorado,
            f"{codigo}_mejorado.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    return _respuesta(generar_pdf(mejorado), f"{codigo}_mejorado.pdf", "application/pdf")
