from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CatalogoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=150)
    unidad: str | None = Field(default=None, min_length=1, max_length=50)
    tipo: Literal["elabora", "revisa"] | None = None

    @model_validator(mode="after")
    def limpiar_textos(self) -> "CatalogoCreate":
        self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValueError("El nombre no puede estar vacío")
        if self.unidad is not None:
            self.unidad = self.unidad.strip()
            if not self.unidad:
                raise ValueError("La unidad no puede estar vacía")
        return self


class CatalogoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    unidad: str | None = Field(default=None, min_length=1, max_length=50)
    tipo: Literal["elabora", "revisa"] | None = None
    activo: bool | None = None

    @model_validator(mode="after")
    def limpiar_textos(self) -> "CatalogoUpdate":
        for campo in ("nombre", "unidad"):
            valor = getattr(self, campo)
            if valor is not None:
                valor = valor.strip()
                if not valor:
                    raise ValueError(f"{campo.capitalize()} no puede estar vacío")
                setattr(self, campo, valor)
        return self


class CatalogoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    orden: int | None = None
    activo: bool
    unidad: str | None = None
    tipo: Literal["elabora", "revisa"] | None = None
