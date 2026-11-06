from typing import Literal

from sqlalchemy import Boolean, CheckConstraint, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CatalogoBase:
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, server_default=true(), nullable=False)


class Colaborador(CatalogoBase, Base):
    __tablename__ = "colaboradores"


class Herramienta(CatalogoBase, Base):
    __tablename__ = "herramientas"


class Material(CatalogoBase, Base):
    __tablename__ = "materiales"

    unidad: Mapped[str] = mapped_column(String(50), nullable=False)


class Firmante(Base):
    __tablename__ = "firmantes"
    __table_args__ = (CheckConstraint("tipo IN ('elabora', 'revisa')", name="tipo_valido"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo: Mapped[Literal["elabora", "revisa"]] = mapped_column(String(10), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, server_default=true(), nullable=False)
