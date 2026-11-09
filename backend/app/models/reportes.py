from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.catalogos import Colaborador, Firmante, Herramienta, Material

TEXTO_FOTOS_PREDETERMINADO = "Fotos antes y después de la actividad realizada"
LETRAS_ACTIVIDAD = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J")
LETRAS_ACTIVIDAD_SQL = ", ".join(f"'{letra}'" for letra in LETRAS_ACTIVIDAD)


class Reporte(Base):
    __tablename__ = "reportes"
    __table_args__ = (UniqueConstraint("anio", "semana"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    semana: Mapped[int] = mapped_column(Integer, nullable=False)
    elaborado_por_id: Mapped[int | None] = mapped_column(ForeignKey("firmantes.id"))
    revisado_por_id: Mapped[int | None] = mapped_column(ForeignKey("firmantes.id"))
    elaborado_por: Mapped["Firmante | None"] = relationship(foreign_keys=[elaborado_por_id])
    revisado_por: Mapped["Firmante | None"] = relationship(foreign_keys=[revisado_por_id])
    dias: Mapped[list["Dia"]] = relationship(
        back_populates="reporte", cascade="all, delete-orphan", order_by="Dia.dia_semana"
    )


class Dia(Base):
    __tablename__ = "dias"
    __table_args__ = (
        UniqueConstraint("reporte_id", "dia_semana"),
        CheckConstraint("dia_semana BETWEEN 0 AND 5", name="dia_semana_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reporte_id: Mapped[int] = mapped_column(ForeignKey("reportes.id", ondelete="CASCADE"))
    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    observacion: Mapped[str] = mapped_column(Text, default="", nullable=False)
    texto_fotos: Mapped[str] = mapped_column(
        Text, default=TEXTO_FOTOS_PREDETERMINADO, nullable=False
    )
    reporte: Mapped[Reporte] = relationship(back_populates="dias")
    actividades: Mapped[list["Actividad"]] = relationship(
        back_populates="dia", cascade="all, delete-orphan", order_by="Actividad.letra"
    )
    herramientas: Mapped[list["DiaHerramienta"]] = relationship(cascade="all, delete-orphan")
    materiales: Mapped[list["DiaMaterial"]] = relationship(cascade="all, delete-orphan")
    fotos: Mapped[list["Foto"]] = relationship(
        back_populates="dia", cascade="all, delete-orphan", order_by="Foto.orden"
    )


class Actividad(Base):
    __tablename__ = "actividades"
    __table_args__ = (
        UniqueConstraint("dia_id", "letra"),
        CheckConstraint(
            f"letra IN ({LETRAS_ACTIVIDAD_SQL})",
            name="letra_valida",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dia_id: Mapped[int] = mapped_column(ForeignKey("dias.id", ondelete="CASCADE"))
    letra: Mapped[str] = mapped_column(String(1), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    dia: Mapped[Dia] = relationship(back_populates="actividades")
    asignaciones: Mapped[list["Asignacion"]] = relationship(
        back_populates="actividad", cascade="all, delete-orphan"
    )


class Asignacion(Base):
    __tablename__ = "asignaciones"
    __table_args__ = (UniqueConstraint("actividad_id", "colaborador_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    actividad_id: Mapped[int] = mapped_column(ForeignKey("actividades.id", ondelete="CASCADE"))
    colaborador_id: Mapped[int] = mapped_column(ForeignKey("colaboradores.id"))
    horas: Mapped[float] = mapped_column(Float, nullable=False)
    horas_manual: Mapped[bool] = mapped_column(Boolean, server_default=false(), nullable=False)
    actividad: Mapped[Actividad] = relationship(back_populates="asignaciones")
    colaborador: Mapped["Colaborador"] = relationship()


class DiaHerramienta(Base):
    __tablename__ = "dia_herramientas"

    dia_id: Mapped[int] = mapped_column(ForeignKey("dias.id", ondelete="CASCADE"), primary_key=True)
    herramienta_id: Mapped[int] = mapped_column(ForeignKey("herramientas.id"), primary_key=True)
    cantidad: Mapped[float] = mapped_column(Float, nullable=False)
    herramienta: Mapped["Herramienta"] = relationship()


class DiaMaterial(Base):
    __tablename__ = "dia_materiales"

    dia_id: Mapped[int] = mapped_column(ForeignKey("dias.id", ondelete="CASCADE"), primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id"), primary_key=True)
    cantidad: Mapped[float] = mapped_column(Float, nullable=False)
    material: Mapped["Material"] = relationship()


class Foto(Base):
    __tablename__ = "fotos"
    __table_args__ = (
        CheckConstraint(
            f"espacio IN ({LETRAS_ACTIVIDAD_SQL}, 'AD')",
            name="espacio_valido",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dia_id: Mapped[int] = mapped_column(ForeignKey("dias.id", ondelete="CASCADE"))
    espacio: Mapped[str] = mapped_column(String(2), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    dia: Mapped[Dia] = relationship(back_populates="fotos")
