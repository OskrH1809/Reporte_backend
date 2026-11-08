from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Letra = Literal["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
Espacio = Literal["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "AD"]


class ReporteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anio: int = Field(ge=2000, le=2100)
    semana: int = Field(ge=1, le=53)

    @model_validator(mode="after")
    def semana_iso_valida(self) -> "ReporteCreate":
        try:
            date.fromisocalendar(self.anio, self.semana, 1)
        except ValueError as error:
            raise ValueError("La semana no existe en el año indicado") from error
        return self


class ReporteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    elaborado_por_id: int | None = Field(default=None, ge=1)
    revisado_por_id: int | None = Field(default=None, ge=1)


class ReporteRead(BaseModel):
    id: int
    anio: int
    semana: int
    codigo: str
    fecha_inicio: date
    fecha_fin: date
    elaborado_por_id: int | None
    revisado_por_id: int | None
    horas_hombre: float


class AsignacionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    colaborador_id: int = Field(ge=1)
    horas: float | None = Field(default=None, ge=0, le=24)
    horas_manual: bool = False

    @model_validator(mode="after")
    def horas_manual_requiere_valor(self) -> "AsignacionWrite":
        if self.horas_manual and self.horas is None:
            raise ValueError("Las horas son obligatorias al usar captura manual")
        return self


class ActividadWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    letra: Letra
    descripcion: str = Field(max_length=1000)
    asignaciones: list[AsignacionWrite] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def asignaciones_unicas(self) -> "ActividadWrite":
        ids = [item.colaborador_id for item in self.asignaciones]
        if len(ids) != len(set(ids)):
            raise ValueError("No se puede repetir un colaborador en una actividad")
        self.descripcion = self.descripcion.strip()
        return self


class CantidadHerramientaWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    herramienta_id: int = Field(ge=1)
    cantidad: float = Field(gt=0, le=100000)


class CantidadMaterialWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material_id: int = Field(ge=1)
    cantidad: float = Field(gt=0, le=100000)


class DiaWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observacion: str = Field(default="", max_length=2000)
    texto_fotos: str = Field(default="", max_length=1000)
    actividades: list[ActividadWrite] = Field(default_factory=list, max_length=10)
    herramientas: list[CantidadHerramientaWrite] = Field(default_factory=list, max_length=100)
    materiales: list[CantidadMaterialWrite] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def listas_unicas(self) -> "DiaWrite":
        grupos = (
            [item.letra for item in self.actividades],
            [item.herramienta_id for item in self.herramientas],
            [item.material_id for item in self.materiales],
        )
        if any(len(items) != len(set(items)) for items in grupos):
            raise ValueError("Las actividades y cantidades no pueden repetirse")
        self.observacion = self.observacion.strip()
        self.texto_fotos = self.texto_fotos.strip()
        return self


class AsignacionRead(BaseModel):
    id: int
    colaborador_id: int
    colaborador_nombre: str
    horas: float
    horas_manual: bool


class ActividadRead(BaseModel):
    id: int
    letra: Letra
    descripcion: str
    asignaciones: list[AsignacionRead]
    personas: int
    horas_hombre: float


class CantidadHerramientaRead(BaseModel):
    herramienta_id: int
    nombre: str
    cantidad: float


class CantidadMaterialRead(BaseModel):
    material_id: int
    nombre: str
    unidad: str
    cantidad: float


class FotoRead(BaseModel):
    id: int
    espacio: Espacio
    orden: int
    nombre_original: str
    url: str


class DiaRead(BaseModel):
    id: int
    dia_semana: int
    fecha: date
    observacion: str
    texto_fotos: str
    actividades: list[ActividadRead]
    herramientas: list[CantidadHerramientaRead]
    materiales: list[CantidadMaterialRead]
    fotos: list[FotoRead]
    personas: int
    horas_hombre: float
    numero_actividades: int
    advertencias: list[str]
