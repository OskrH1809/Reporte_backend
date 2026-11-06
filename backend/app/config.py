from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)

    database_url: str = "sqlite:////data/app.db"
    test_database_url: str = "sqlite+pysqlite:///:memory:"
    environment: Literal["local", "test"] = "local"
    cors_origins: Annotated[list[str], NoDecode] = []
    jornada_semana: float = Field(8, gt=0, le=24)
    jornada_sabado: float = Field(5, gt=0, le=24)
    max_foto_mb: int = Field(15, ge=1, le=20)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
