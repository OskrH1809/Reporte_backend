import json
import secrets
from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

LARGO_MINIMO_SECRETO = 32


class AdminSemilla(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correo: str = Field(min_length=3, max_length=254)
    contrasena_hash: SecretStr

    @field_validator("correo")
    @classmethod
    def correo_normalizado(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if "@" not in valor:
            raise ValueError("El correo del administrador no es válido")
        return valor

    @field_validator("contrasena_hash")
    @classmethod
    def solo_hash_argon2(cls, valor: SecretStr) -> SecretStr:
        # Evita que una contraseña en claro termine en las variables de entorno.
        if not valor.get_secret_value().startswith("$argon2"):
            raise ValueError("contrasena_hash debe ser un hash argon2 ($argon2…)")
        return valor


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)

    database_url: str = "sqlite:////data/app.db"
    test_database_url: str = "sqlite+pysqlite:///:memory:"
    environment: Literal["local", "test", "production"] = "local"
    cors_origins: Annotated[list[str], NoDecode] = []
    jornada_semana: float = Field(8, gt=0, le=24)
    jornada_sabado: float = Field(5, gt=0, le=24)
    max_foto_mb: int = Field(15, ge=1, le=20)
    autenticacion: bool = False
    jwt_secreto: SecretStr | None = None
    jwt_minutos: int = Field(480, ge=5, le=1440)
    admins_semilla: Annotated[list[AdminSemilla], NoDecode] = []

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalizar_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        for prefijo in ("postgres://", "postgresql://"):
            if value.startswith(prefijo):
                value = "postgresql+psycopg://" + value[len(prefijo) :]
                break
        if value.startswith("postgresql"):
            partes = urlsplit(value)
            parametros = dict(parse_qsl(partes.query))
            parametros.setdefault("sslmode", "require")
            value = urlunsplit(partes._replace(query=urlencode(parametros)))
        return value

    @field_validator("admins_semilla", mode="before")
    @classmethod
    def leer_admins_semilla(cls, value: object) -> object:
        if isinstance(value, str):
            if not value.strip():
                return []
            try:
                return json.loads(value)
            except json.JSONDecodeError as error:
                raise ValueError("ADMINS_SEMILLA debe ser una lista JSON") from error
        return value

    @model_validator(mode="after")
    def secreto_jwt(self) -> "Settings":
        if self.jwt_secreto is None:
            if self.autenticacion and self.environment != "test":
                raise ValueError("JWT_SECRETO es obligatorio cuando AUTENTICACION=true")
            # Sin autenticación (o en pruebas) basta un secreto efímero por proceso.
            self.jwt_secreto = SecretStr(secrets.token_urlsafe(48))
        elif len(self.jwt_secreto.get_secret_value()) < LARGO_MINIMO_SECRETO:
            raise ValueError(f"JWT_SECRETO debe tener al menos {LARGO_MINIMO_SECRETO} caracteres")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
