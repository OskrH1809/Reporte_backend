"""Esquema inicial.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "colaboradores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_table(
        "herramientas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_table(
        "materiales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("unidad", sa.String(length=50), nullable=False),
    )
    op.create_table(
        "firmantes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint("tipo IN ('elabora', 'revisa')", name="tipo_valido"),
    )
    op.create_table(
        "reportes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("semana", sa.Integer(), nullable=False),
        sa.Column("elaborado_por_id", sa.Integer(), sa.ForeignKey("firmantes.id")),
        sa.Column("revisado_por_id", sa.Integer(), sa.ForeignKey("firmantes.id")),
        sa.UniqueConstraint("anio", "semana"),
    )
    op.create_table(
        "dias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "reporte_id",
            sa.Integer(),
            sa.ForeignKey("reportes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("observacion", sa.Text(), nullable=False),
        sa.Column("texto_fotos", sa.Text(), nullable=False),
        sa.CheckConstraint("dia_semana BETWEEN 0 AND 5", name="dia_semana_valido"),
        sa.UniqueConstraint("reporte_id", "dia_semana"),
    )
    op.create_table(
        "actividades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dia_id",
            sa.Integer(),
            sa.ForeignKey("dias.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("letra", sa.String(length=1), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.CheckConstraint("letra IN ('A', 'B', 'C')", name="letra_valida"),
        sa.UniqueConstraint("dia_id", "letra"),
    )
    op.create_table(
        "asignaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "actividad_id",
            sa.Integer(),
            sa.ForeignKey("actividades.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "colaborador_id", sa.Integer(), sa.ForeignKey("colaboradores.id"), nullable=False
        ),
        sa.Column("horas", sa.Float(), nullable=False),
        sa.Column("horas_manual", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.UniqueConstraint("actividad_id", "colaborador_id"),
    )
    op.create_table(
        "dia_herramientas",
        sa.Column(
            "dia_id",
            sa.Integer(),
            sa.ForeignKey("dias.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "herramienta_id",
            sa.Integer(),
            sa.ForeignKey("herramientas.id"),
            primary_key=True,
        ),
        sa.Column("cantidad", sa.Float(), nullable=False),
    )
    op.create_table(
        "dia_materiales",
        sa.Column(
            "dia_id",
            sa.Integer(),
            sa.ForeignKey("dias.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "material_id",
            sa.Integer(),
            sa.ForeignKey("materiales.id"),
            primary_key=True,
        ),
        sa.Column("cantidad", sa.Float(), nullable=False),
    )
    op.create_table(
        "fotos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dia_id",
            sa.Integer(),
            sa.ForeignKey("dias.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("espacio", sa.String(length=2), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("archivo", sa.String(length=255), nullable=False),
        sa.Column("nombre_original", sa.String(length=255), nullable=False),
        sa.CheckConstraint("espacio IN ('A', 'B', 'C', 'AD')", name="espacio_valido"),
    )


def downgrade() -> None:
    op.drop_table("fotos")
    op.drop_table("dia_materiales")
    op.drop_table("dia_herramientas")
    op.drop_table("asignaciones")
    op.drop_table("actividades")
    op.drop_table("dias")
    op.drop_table("reportes")
    op.drop_table("firmantes")
    op.drop_table("materiales")
    op.drop_table("herramientas")
    op.drop_table("colaboradores")
