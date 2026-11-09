"""Amplía las actividades y espacios de fotos hasta la letra J.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LETRAS_A_J = "'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'"


def _cambiar_restriccion(tabla: str, nombre: str, condicion: str) -> None:
    if op.get_bind().dialect.name == "sqlite":
        # SQLite no altera restricciones: hay que recrear la tabla.
        with op.batch_alter_table(tabla, recreate="always") as batch_op:
            batch_op.drop_constraint(nombre, type_="check")
            batch_op.create_check_constraint(nombre, condicion)
    else:
        # Recrear la tabla en Postgres falla por las llaves foráneas que la referencian.
        op.drop_constraint(nombre, tabla, type_="check")
        op.create_check_constraint(nombre, tabla, condicion)


def upgrade() -> None:
    _cambiar_restriccion("actividades", "letra_valida", f"letra IN ({LETRAS_A_J})")
    _cambiar_restriccion("fotos", "espacio_valido", f"espacio IN ({LETRAS_A_J}, 'AD')")


def downgrade() -> None:
    # Bajar borra actividades y fotos D–J.
    op.execute(
        "DELETE FROM asignaciones WHERE actividad_id IN "
        "(SELECT id FROM actividades WHERE letra NOT IN ('A', 'B', 'C'))"
    )
    op.execute("DELETE FROM actividades WHERE letra NOT IN ('A', 'B', 'C')")
    op.execute("DELETE FROM fotos WHERE espacio NOT IN ('A', 'B', 'C', 'AD')")
    _cambiar_restriccion("actividades", "letra_valida", "letra IN ('A', 'B', 'C')")
    _cambiar_restriccion("fotos", "espacio_valido", "espacio IN ('A', 'B', 'C', 'AD')")
