from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Colaborador, Herramienta, Material, Reporte
from app.services import fotos


@dataclass
class NombreMemoria:
    nombre: str
    unidad: str = ""


@dataclass
class AsignacionMemoria:
    colaborador_id: int
    colaborador: NombreMemoria
    horas: float
    horas_manual: bool


@dataclass
class ActividadMemoria:
    letra: str
    descripcion: str
    asignaciones: list[AsignacionMemoria] = field(default_factory=list)


@dataclass
class CantidadMemoria:
    cantidad: float
    herramienta_id: int | None = None
    herramienta: NombreMemoria | None = None
    material_id: int | None = None
    material: NombreMemoria | None = None


@dataclass
class FotoMemoria:
    espacio: str
    orden: int
    contenido: bytes


@dataclass
class DiaMemoria:
    dia_semana: int
    fecha: date
    observacion: str = ""
    texto_fotos: str = ""
    actividades: list[ActividadMemoria] = field(default_factory=list)
    herramientas: list[CantidadMemoria] = field(default_factory=list)
    materiales: list[CantidadMemoria] = field(default_factory=list)
    fotos: list[FotoMemoria] = field(default_factory=list)


@dataclass
class ReporteMemoria:
    anio: int
    semana: int
    elaborado_por: NombreMemoria | None = None
    revisado_por: NombreMemoria | None = None
    dias: list[DiaMemoria] = field(default_factory=list)


def _nombre(item, *, con_unidad: bool = False) -> NombreMemoria:
    return NombreMemoria(
        nombre=item.nombre,
        unidad=item.unidad if con_unidad else "",
    )


def desde_orm(reporte: Reporte) -> ReporteMemoria:
    dias = []
    for dia in reporte.dias:
        fotos_memoria = []
        for foto in dia.fotos:
            ruta = fotos.FOTOS_DIR / Path(foto.archivo).name
            if ruta.is_file():
                fotos_memoria.append(
                    FotoMemoria(espacio=foto.espacio, orden=foto.orden, contenido=ruta.read_bytes())
                )
        dias.append(
            DiaMemoria(
                dia_semana=dia.dia_semana,
                fecha=dia.fecha,
                observacion=dia.observacion,
                texto_fotos=dia.texto_fotos,
                actividades=[
                    ActividadMemoria(
                        letra=actividad.letra,
                        descripcion=actividad.descripcion,
                        asignaciones=[
                            AsignacionMemoria(
                                colaborador_id=asignacion.colaborador_id,
                                colaborador=_nombre(asignacion.colaborador),
                                horas=asignacion.horas,
                                horas_manual=asignacion.horas_manual,
                            )
                            for asignacion in actividad.asignaciones
                        ],
                    )
                    for actividad in dia.actividades
                ],
                herramientas=[
                    CantidadMemoria(
                        herramienta_id=item.herramienta_id,
                        herramienta=_nombre(item.herramienta),
                        cantidad=item.cantidad,
                    )
                    for item in dia.herramientas
                ],
                materiales=[
                    CantidadMemoria(
                        material_id=item.material_id,
                        material=_nombre(item.material, con_unidad=True),
                        cantidad=item.cantidad,
                    )
                    for item in dia.materiales
                ],
                fotos=fotos_memoria,
            )
        )
    return ReporteMemoria(
        anio=reporte.anio,
        semana=reporte.semana,
        elaborado_por=_nombre(reporte.elaborado_por) if reporte.elaborado_por else None,
        revisado_por=_nombre(reporte.revisado_por) if reporte.revisado_por else None,
        dias=dias,
    )


def catalogos_exportacion(
    session: Session, *, solo_activos: bool
) -> tuple[list[Colaborador], list[Herramienta], list[Material]]:
    consulta_colaboradores = select(Colaborador).order_by(Colaborador.orden, Colaborador.id)
    consulta_herramientas = select(Herramienta).order_by(Herramienta.orden, Herramienta.id)
    consulta_materiales = select(Material).order_by(Material.orden, Material.id)
    if solo_activos:
        consulta_colaboradores = consulta_colaboradores.where(Colaborador.activo.is_(True))
        consulta_herramientas = consulta_herramientas.where(Herramienta.activo.is_(True))
        consulta_materiales = consulta_materiales.where(Material.activo.is_(True))
    return (
        list(session.scalars(consulta_colaboradores)),
        list(session.scalars(consulta_herramientas)),
        list(session.scalars(consulta_materiales)),
    )
