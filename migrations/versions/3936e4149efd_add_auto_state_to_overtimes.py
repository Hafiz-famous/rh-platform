"""add auto_state to overtimes

Revision ID: 3936e4149efd
Revises: 8484db28f7f4
Create Date: 2025-09-01 10:52:22.849234

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3936e4149efd'
down_revision = '8484db28f7f4'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("overtimes")}

    # Ajoute la colonne seulement si elle n'existe pas (idempotent)
    if "auto_state" not in cols:
        op.add_column(
            "overtimes",
            sa.Column("auto_state", sa.Text(), nullable=True)  # laisse nullable pour éviter les ALTER compliqués sous SQLite
        )

def downgrade():
    # Optionnel: suppression sûre (batch géré par env.py pour SQLite)
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("overtimes")}
    if "auto_state" in cols:
        with op.batch_alter_table("overtimes", schema=None) as batch_op:
            batch_op.drop_column("auto_state")