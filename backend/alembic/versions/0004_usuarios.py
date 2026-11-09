"""Usuarios para el inicio de sesión.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("correo", sa.String(length=254), nullable=False),
        sa.Column("contrasena_hash", sa.String(length=255), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("intentos_fallidos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("correo"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE "usuarios" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_table("usuarios")
