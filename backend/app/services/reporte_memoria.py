from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidInputError, NotFoundError
from app.models import Colaborador, Firmante, Herramienta, Material, Reporte
from app.models.reportes import TEXTO_FOTOS_PREDETERMINADO
from app.schemas.exportar import ReporteExportar
from app.services import fotos
from app.services.calculos import jornada_dia, recalcular_horas


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


def armar_reporte(
    datos: ReporteExportar, contenidos: list[bytes], session: Session
) -> ReporteMemoria:
    elaborado_por = _firmante(session, datos.elaborado_por_id)
    revisado_por = _firmante(session, datos.revisado_por_id)
    lunes = date.fromisocalendar(datos.anio, datos.semana, 1)
    dias = []
    for entrada in sorted(datos.dias, key=lambda item: item.dia_semana):
        actividades = []
        for actividad in sorted(entrada.actividades, key=lambda item: item.letra):
            asignaciones = []
            for asignacion in actividad.asignaciones:
                colaborador = session.get(Colaborador, asignacion.colaborador_id)
                if colaborador is None:
                    raise NotFoundError("Colaborador no encontrado")
                asignaciones.append(
                    AsignacionMemoria(
                        colaborador_id=colaborador.id,
                        colaborador=_nombre(colaborador),
                        horas=asignacion.horas or 0,
                        horas_manual=asignacion.horas_manual,
                    )
                )
            actividades.append(
                ActividadMemoria(
                    letra=actividad.letra,
                    descripcion=actividad.descripcion,
                    asignaciones=asignaciones,
                )
            )
        herramientas = []
        for cantidad in entrada.herramientas:
            herramienta = session.get(Herramienta, cantidad.herramienta_id)
            if herramienta is None:
                raise NotFoundError("Herramienta no encontrada")
            herramientas.append(
                CantidadMemoria(
                    cantidad=cantidad.cantidad,
                    herramienta_id=herramienta.id,
                    herramienta=_nombre(herramienta),
                )
            )
        materiales = []
        for cantidad in entrada.materiales:
            material = session.get(Material, cantidad.material_id)
            if material is None:
                raise NotFoundError("Material no encontrado")
            materiales.append(
                CantidadMemoria(
                    cantidad=cantidad.cantidad,
                    material_id=material.id,
                    material=_nombre(material, con_unidad=True),
                )
            )
        ordenes: dict[str, int] = defaultdict(int)
        fotos_memoria = []
        for foto in entrada.fotos:
            if foto.indice >= len(contenidos):
                raise InvalidInputError("Foto no encontrada en la petición")
            ordenes[foto.espacio] += 1
            fotos_memoria.append(
                FotoMemoria(
                    espacio=foto.espacio,
                    orden=ordenes[foto.espacio],
                    contenido=contenidos[foto.indice],
                )
            )
        dia = DiaMemoria(
            dia_semana=entrada.dia_semana,
            fecha=lunes + timedelta(days=entrada.dia_semana),
            observacion=entrada.observacion,
            texto_fotos=entrada.texto_fotos or TEXTO_FOTOS_PREDETERMINADO,
            actividades=actividades,
            herramientas=herramientas,
            materiales=materiales,
            fotos=fotos_memoria,
        )
        recalcular_horas(dia, jornada_dia(dia))
        dias.append(dia)
    return ReporteMemoria(
        anio=datos.anio,
        semana=datos.semana,
        elaborado_por=elaborado_por,
        revisado_por=revisado_por,
        dias=dias,
    )


def _firmante(session: Session, firmante_id: int | None) -> NombreMemoria | None:
    if firmante_id is None:
        return None
    firmante = session.get(Firmante, firmante_id)
    if firmante is None:
        raise NotFoundError("Firmante no encontrado")
    return _nombre(firmante)
