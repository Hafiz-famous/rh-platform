from alembic import op
import sqlalchemy as sa

revision = "6d0f57a444a7"
down_revision = "76eb22c110c6"  # comme avant
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # --- Colonnes existantes ?
    cols = {c["name"] for c in insp.get_columns("leaves")}

    # 1) Colonnes d'audit (ADD COLUMN est supporté par SQLite)
    if "validated_by_id" not in cols:
        op.add_column("leaves", sa.Column("validated_by_id", sa.Integer(), nullable=True))
    if "validated_at" not in cols:
        op.add_column("leaves", sa.Column("validated_at", sa.DateTime(), nullable=True))
    if "notified_at" not in cols:
        op.add_column("leaves", sa.Column("notified_at", sa.DateTime(), nullable=True))

    # 2) Index sur validated_by_id (si absent)
    idx_names = {ix["name"] for ix in insp.get_indexes("leaves")}
    if "ix_leaves_validated_by_id" not in idx_names:
        op.create_index("ix_leaves_validated_by_id", "leaves", ["validated_by_id"], unique=False)

    # 3) FK validated_by_id -> users.id (en batch pour SQLite)
    fks = insp.get_foreign_keys("leaves")
    has_fk = any(
        ("validated_by_id" in fk.get("constrained_columns", [])) and (fk.get("referred_table") == "users")
        for fk in fks
    )
    if not has_fk:
        with op.batch_alter_table("leaves", schema=None) as batch_op:
            batch_op.create_foreign_key(
                "fk_leaves_validated_by",
                "users",
                ["validated_by_id"],
                ["id"],
                # ondelete="SET NULL",  # décommente si voulu et si la colonne est nullable
            )


def downgrade():
    # Non destructif par choix (éviter d'effacer des colonnes en prod)
    pass
