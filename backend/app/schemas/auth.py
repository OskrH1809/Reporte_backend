from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correo: str = Field(min_length=3, max_length=254)
    contrasena: str = Field(min_length=1, max_length=128)

    @field_validator("correo")
    @classmethod
    def correo_normalizado(cls, valor: str) -> str:
        return valor.strip().lower()


class LoginSalida(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - tipo de token, no contraseña
    expira_en: datetime


class UsuarioSalida(BaseModel):
    id: int
    correo: str
