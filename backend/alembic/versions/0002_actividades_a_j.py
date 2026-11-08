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


def upgrade() -> None:
    with op.batch_alter_table("actividades", recreate="always") as batch_op:
        batch_op.drop_constraint("letra_valida", type_="check")
        batch_op.create_check_constraint("letra_valida", f"letra IN ({LETRAS_A_J})")
    with op.batch_alter_table("fotos", recreate="always") as batch_op:
        batch_op.drop_constraint("espacio_valido", type_="check")
        batch_op.create_check_constraint("espacio_valido", f"espacio IN ({LETRAS_A_J}, 'AD')")


def downgrade() -> None:
    # Bajar borra actividades y fotos D–J.
    op.execute(
        "DELETE FROM asignaciones WHERE actividad_id IN "
        "(SELECT id FROM actividades WHERE letra NOT IN ('A', 'B', 'C'))"
    )
    op.execute("DELETE FROM actividades WHERE letra NOT IN ('A', 'B', 'C')")
    op.execute("DELETE FROM fotos WHERE espacio NOT IN ('A', 'B', 'C', 'AD')")
    with op.batch_alter_table("actividades", recreate="always") as batch_op:
        batch_op.drop_constraint("letra_valida", type_="check")
        batch_op.create_check_constraint("letra_valida", "letra IN ('A', 'B', 'C')")
    with op.batch_alter_table("fotos", recreate="always") as batch_op:
        batch_op.drop_constraint("espacio_valido", type_="check")
        batch_op.create_check_constraint("espacio_valido", "espacio IN ('A', 'B', 'C', 'AD')")
