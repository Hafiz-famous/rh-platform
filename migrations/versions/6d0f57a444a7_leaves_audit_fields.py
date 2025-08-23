from alembic import op
import sqlalchemy as sa

revision = "6d0f57a444a7"
down_revision = "76eb22c110c6"  # comme avant
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Ajoute les colonnes d'audit seulement si elles n'existent pas déjà
    cols = {c["name"] for c in insp.get_columns("leaves")}

    if "validated_by_id" not in cols:
        op.add_column("leaves", sa.Column("validated_by_id", sa.Integer(), nullable=True))
        # FK vers users.id si elle n'existe pas déjà
        fks = insp.get_foreign_keys("leaves")
        has_fk = any(fk.get("constrained_columns") == ["validated_by_id"] for fk in fks)
        if not has_fk:
            op.create_foreign_key(None, "leaves", "users", ["validated_by_id"], ["id"])
        # index utile
        op.create_index("ix_leaves_validated_by_id", "leaves", ["validated_by_id"], unique=False)

    if "validated_at" not in cols:
        op.add_column("leaves", sa.Column("validated_at", sa.DateTime(), nullable=True))

    if "notified_at" not in cols:
        op.add_column("leaves", sa.Column("notified_at", sa.DateTime(), nullable=True))

def downgrade():
    # On laisse vide pour éviter d'effacer des colonnes utiles en prod
    pass
