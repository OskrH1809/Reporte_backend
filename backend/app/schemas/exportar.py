from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.reportes import DiaWrite, Espacio, ReporteCreate


class FotoExportar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indice: int = Field(ge=0)
    espacio: Espacio


class DiaExportar(DiaWrite):
    dia_semana: int = Field(ge=0, le=5)
    fotos: list[FotoExportar] = Field(default_factory=list, max_length=44)

    @model_validator(mode="after")
    def fotos_por_espacio(self) -> "DiaExportar":
        espacios = [foto.espacio for foto in self.fotos]
        if any(espacios.count(espacio) > 4 for espacio in set(espacios)):
            raise ValueError("Cada espacio admite como máximo 4 fotos")
        return self


class ReporteExportar(ReporteCreate):
    elaborado_por_id: int | None = Field(default=None, ge=1)
    revisado_por_id: int | None = Field(default=None, ge=1)
    dias: list[DiaExportar] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def dias_e_indices_unicos(self) -> "ReporteExportar":
        dias = [dia.dia_semana for dia in self.dias]
        if len(dias) != len(set(dias)):
            raise ValueError("Los días de la semana no pueden repetirse")
        indices = [foto.indice for dia in self.dias for foto in dia.fotos]
        if len(indices) != len(set(indices)):
            raise ValueError("Los índices de foto no pueden repetirse")
        return self
