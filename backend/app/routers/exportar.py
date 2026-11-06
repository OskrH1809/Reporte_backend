from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers.reportes import obtener_reporte
from app.services.excel_formato import generar_formato
from app.services.excel_mejorado import generar_mejorado
from app.services.pdf import generar_pdf

DatabaseSession = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/api/reportes", tags=["exportacion"])


def _respuesta(contenido: bytes, nombre: str, media_type: str) -> Response:
    return Response(
        content=contenido,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{reporte_id}/exportar/{tipo}", response_model=None)
def exportar(
    reporte_id: int,
    tipo: Literal["formato", "mejorado", "pdf"],
    session: DatabaseSession,
) -> Response:
    reporte = obtener_reporte(session, reporte_id)
    codigo = f"CH-RSG-{reporte.semana}-{reporte.anio}"
    if tipo == "formato":
        return _respuesta(
            generar_formato(reporte),
            f"{codigo}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    mejorado = generar_mejorado(reporte)
    if tipo == "mejorado":
        return _respuesta(
            mejorado,
            f"{codigo}_mejorado.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    return _respuesta(generar_pdf(mejorado), f"{codigo}_mejorado.pdf", "application/pdf")
