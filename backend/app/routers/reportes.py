from datetime import date, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db import get_db
from app.errors import DuplicateReportError, NotFoundError, SpaceFullError
from app.models import (
    Actividad,
    Asignacion,
    Colaborador,
    Dia,
    DiaHerramienta,
    DiaMaterial,
    Firmante,
    Foto,
    Herramienta,
    Material,
    Reporte,
)
from app.schemas.reportes import (
    ActividadRead,
    AsignacionRead,
    DiaRead,
    DiaWrite,
    FotoRead,
    ReporteCreate,
    ReporteRead,
    ReporteUpdate,
)
from app.services import fotos
from app.services.calculos import recalcular_horas, totales_dia

DatabaseSession = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/api", tags=["reportes"])
settings = get_settings()
LIMITES_FOTOS = {"A": 2, "B": 4, "C": 2, "AD": 4}


def obtener_reporte(session: Session, reporte_id: int) -> Reporte:
    consulta = (
        select(Reporte)
        .where(Reporte.id == reporte_id)
        .options(
            selectinload(Reporte.dias)
            .selectinload(Dia.actividades)
            .selectinload(Actividad.asignaciones)
            .selectinload(Asignacion.colaborador),
            selectinload(Reporte.dias)
            .selectinload(Dia.herramientas)
            .selectinload(DiaHerramienta.herramienta),
            selectinload(Reporte.dias)
            .selectinload(Dia.materiales)
            .selectinload(DiaMaterial.material),
            selectinload(Reporte.dias).selectinload(Dia.fotos),
            selectinload(Reporte.elaborado_por),
            selectinload(Reporte.revisado_por),
        )
    )
    reporte = session.scalar(consulta)
    if reporte is None:
        raise NotFoundError("Reporte no encontrado")
    return reporte


def obtener_dia(session: Session, reporte_id: int, dia_semana: int) -> Dia:
    reporte = obtener_reporte(session, reporte_id)
    dia = next((item for item in reporte.dias if item.dia_semana == dia_semana), None)
    if dia is None:
        raise NotFoundError("Día no encontrado")
    return dia


def _jornada(dia: Dia) -> float:
    return settings.jornada_sabado if dia.dia_semana == 5 else settings.jornada_semana


def serializar_dia(dia: Dia) -> DiaRead:
    personas, horas_hombre, numero_actividades, advertencias = totales_dia(dia, _jornada(dia))
    actividades = []
    for actividad in dia.actividades:
        asignaciones = [
            AsignacionRead(
                id=item.id,
                colaborador_id=item.colaborador_id,
                colaborador_nombre=item.colaborador.nombre,
                horas=item.horas,
                horas_manual=item.horas_manual,
            )
            for item in actividad.asignaciones
        ]
        actividades.append(
            ActividadRead(
                id=actividad.id,
                letra=actividad.letra,
                descripcion=actividad.descripcion,
                asignaciones=asignaciones,
                personas=len(asignaciones),
                horas_hombre=round(sum(item.horas for item in actividad.asignaciones), 2),
            )
        )
    return DiaRead(
        id=dia.id,
        dia_semana=dia.dia_semana,
        fecha=dia.fecha,
        observacion=dia.observacion,
        texto_fotos=dia.texto_fotos,
        actividades=actividades,
        herramientas=[
            {
                "herramienta_id": item.herramienta_id,
                "nombre": item.herramienta.nombre,
                "cantidad": item.cantidad,
            }
            for item in dia.herramientas
        ],
        materiales=[
            {
                "material_id": item.material_id,
                "nombre": item.material.nombre,
                "unidad": item.material.unidad,
                "cantidad": item.cantidad,
            }
            for item in dia.materiales
        ],
        fotos=[
            FotoRead(
                id=item.id,
                espacio=item.espacio,
                orden=item.orden,
                nombre_original=item.nombre_original,
                url=f"/api/fotos/{item.id}/archivo",
            )
            for item in dia.fotos
        ],
        personas=personas,
        horas_hombre=horas_hombre,
        numero_actividades=numero_actividades,
        advertencias=advertencias,
    )


def serializar_reporte(reporte: Reporte) -> ReporteRead:
    return ReporteRead(
        id=reporte.id,
        anio=reporte.anio,
        semana=reporte.semana,
        codigo=f"CH-RSG-{reporte.semana}-{reporte.anio}",
        fecha_inicio=reporte.dias[0].fecha,
        fecha_fin=reporte.dias[-1].fecha,
        elaborado_por_id=reporte.elaborado_por_id,
        revisado_por_id=reporte.revisado_por_id,
        horas_hombre=round(sum(totales_dia(dia, _jornada(dia))[1] for dia in reporte.dias), 2),
    )


@router.get("/reportes", response_model=list[ReporteRead])
def listar_reportes(session: DatabaseSession) -> list[ReporteRead]:
    ids = session.scalars(select(Reporte.id).order_by(Reporte.anio.desc(), Reporte.semana.desc()))
    return [serializar_reporte(obtener_reporte(session, reporte_id)) for reporte_id in ids]


@router.post("/reportes", response_model=ReporteRead, status_code=status.HTTP_201_CREATED)
def crear_reporte(data: ReporteCreate, session: DatabaseSession) -> ReporteRead:
    lunes = date.fromisocalendar(data.anio, data.semana, 1)
    reporte = Reporte(anio=data.anio, semana=data.semana)
    reporte.dias = [
        Dia(dia_semana=indice, fecha=lunes + timedelta(days=indice)) for indice in range(6)
    ]
    session.add(reporte)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise DuplicateReportError("Ya existe un reporte para esa semana") from error
    return serializar_reporte(obtener_reporte(session, reporte.id))


@router.get("/reportes/{reporte_id}", response_model=ReporteRead)
def ver_reporte(reporte_id: int, session: DatabaseSession) -> ReporteRead:
    return serializar_reporte(obtener_reporte(session, reporte_id))


@router.patch("/reportes/{reporte_id}", response_model=ReporteRead)
def editar_reporte(reporte_id: int, data: ReporteUpdate, session: DatabaseSession) -> ReporteRead:
    reporte = obtener_reporte(session, reporte_id)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        if valor is not None and session.get(Firmante, valor) is None:
            raise NotFoundError("Firmante no encontrado")
        setattr(reporte, campo, valor)
    session.commit()
    return serializar_reporte(obtener_reporte(session, reporte_id))


@router.delete("/reportes/{reporte_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_reporte(reporte_id: int, session: DatabaseSession) -> Response:
    reporte = obtener_reporte(session, reporte_id)
    archivos = [foto.archivo for dia in reporte.dias for foto in dia.fotos]
    session.delete(reporte)
    session.commit()
    for archivo in archivos:
        fotos.eliminar_archivo(archivo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/reportes/{reporte_id}/dias/{dia_semana}", response_model=DiaRead)
def ver_dia(reporte_id: int, dia_semana: int, session: DatabaseSession) -> DiaRead:
    return serializar_dia(obtener_dia(session, reporte_id, dia_semana))


@router.put("/reportes/{reporte_id}/dias/{dia_semana}", response_model=DiaRead)
def guardar_dia(
    reporte_id: int, dia_semana: int, data: DiaWrite, session: DatabaseSession
) -> DiaRead:
    dia = obtener_dia(session, reporte_id, dia_semana)
    dia.observacion = data.observacion
    dia.texto_fotos = data.texto_fotos
    dia.actividades.clear()
    dia.herramientas.clear()
    dia.materiales.clear()
    session.flush()
    for entrada in data.actividades:
        actividad = Actividad(letra=entrada.letra, descripcion=entrada.descripcion)
        for asignacion in entrada.asignaciones:
            if session.get(Colaborador, asignacion.colaborador_id) is None:
                raise NotFoundError("Colaborador no encontrado")
            actividad.asignaciones.append(
                Asignacion(
                    colaborador_id=asignacion.colaborador_id,
                    horas=asignacion.horas or 0,
                    horas_manual=asignacion.horas_manual,
                )
            )
        dia.actividades.append(actividad)
    for entrada in data.herramientas:
        if session.get(Herramienta, entrada.herramienta_id) is None:
            raise NotFoundError("Herramienta no encontrada")
        dia.herramientas.append(DiaHerramienta(**entrada.model_dump()))
    for entrada in data.materiales:
        if session.get(Material, entrada.material_id) is None:
            raise NotFoundError("Material no encontrado")
        dia.materiales.append(DiaMaterial(**entrada.model_dump()))
    recalcular_horas(dia, _jornada(dia))
    session.commit()
    return serializar_dia(obtener_dia(session, reporte_id, dia_semana))


@router.post(
    "/reportes/{reporte_id}/dias/{dia_semana}/fotos",
    response_model=FotoRead,
    status_code=status.HTTP_201_CREATED,
)
def subir_foto(
    reporte_id: int,
    dia_semana: int,
    session: DatabaseSession,
    archivo: Annotated[UploadFile, File()],
    espacio: Annotated[str, Form()],
) -> FotoRead:
    if espacio not in LIMITES_FOTOS:
        raise NotFoundError("Espacio de foto no encontrado")
    dia = obtener_dia(session, reporte_id, dia_semana)
    existentes = [foto for foto in dia.fotos if foto.espacio == espacio]
    if len(existentes) >= LIMITES_FOTOS[espacio]:
        raise SpaceFullError("El espacio ya alcanzó su máximo de fotos")
    contenido = archivo.file.read(settings.max_foto_mb * 1024 * 1024 + 1)
    nombre = fotos.procesar_foto(contenido, settings.max_foto_mb)
    foto = Foto(
        dia_id=dia.id,
        espacio=espacio,
        orden=len(existentes) + 1,
        archivo=nombre,
        nombre_original=Path(archivo.filename or "foto").name[:255],
    )
    session.add(foto)
    session.commit()
    session.refresh(foto)
    return FotoRead(
        id=foto.id,
        espacio=foto.espacio,
        orden=foto.orden,
        nombre_original=foto.nombre_original,
        url=f"/api/fotos/{foto.id}/archivo",
    )


@router.get("/fotos/{foto_id}/archivo", response_model=None)
def descargar_foto(foto_id: int, session: DatabaseSession) -> FileResponse:
    foto = session.get(Foto, foto_id)
    if foto is None:
        raise NotFoundError("Foto no encontrada")
    ruta = fotos.FOTOS_DIR / Path(foto.archivo).name
    if not ruta.is_file():
        raise NotFoundError("Archivo de foto no encontrado")
    return FileResponse(ruta, media_type="image/jpeg", filename=foto.nombre_original)


@router.delete("/fotos/{foto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_foto(foto_id: int, session: DatabaseSession) -> Response:
    foto = session.get(Foto, foto_id)
    if foto is None:
        raise NotFoundError("Foto no encontrada")
    nombre = foto.archivo
    session.delete(foto)
    session.commit()
    fotos.eliminar_archivo(nombre)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
