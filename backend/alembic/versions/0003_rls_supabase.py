"""Activa Row-Level Security en Postgres (Supabase).

Sin políticas: la API de datos de Supabase (roles anon/authenticated) no ve nada,
y el backend, que se conecta como dueño de las tablas, no se ve afectado.
En SQLite no hace nada.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLAS = (
    # alembic_version también: en Supabase el rol anon podría modificarla.
    "alembic_version",
    "actividades",
    "asignaciones",
    "colaboradores",
    "dia_herramientas",
    "dia_materiales",
    "dias",
    "firmantes",
    "fotos",
    "herramientas",
    "materiales",
    "reportes",
)


def _es_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _es_postgres():
        return
    for tabla in TABLAS:
        op.execute(f'ALTER TABLE "{tabla}" ENABLE ROW LEVEL SECURITY')  # noqa: S608 - nombres fijos


def downgrade() -> None:
    if not _es_postgres():
        return
    for tabla in TABLAS:
        op.execute(f'ALTER TABLE "{tabla}" DISABLE ROW LEVEL SECURITY')  # noqa: S608 - nombres fijos
