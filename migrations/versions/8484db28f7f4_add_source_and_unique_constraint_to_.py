"""add source and unique constraint to overtimes

Revision ID: 8484db28f7f4
Revises: edc55a98bc6b
Create Date: 2025-09-01 10:04:06.537949
"""
from alembic import op
import sqlalchemy as sa

revision = "8484db28f7f4"
down_revision = "edc55a98bc6b"
branch_labels = None
depends_on = None

def upgrade():
    from alembic import op
    import sqlalchemy as sa

    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1) Ajouter la colonne 'source' seulement si absente
    cols = {c["name"] for c in insp.get_columns("overtimes")}
    if "source" not in cols:
        op.add_column(
            "overtimes",
            sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        )

    # 2) Unicité (SQLite => index unique ; autres => contrainte unique)
    if bind.dialect.name == "sqlite":
        existing_idx = {ix["name"] for ix in insp.get_indexes("overtimes")}
        if "uq_overtimes_user_date_source" not in existing_idx:
            op.create_index(
                "uq_overtimes_user_date_source",
                "overtimes",
                ["user_id", "work_date", "source"],
                unique=True,
            )
    else:
        try:
            uqs = insp.get_unique_constraints("overtimes")
            has_uq = any(uq.get("name") == "uq_overtimes_user_date_source" for uq in uqs)
        except NotImplementedError:
            has_uq = False
        if not has_uq:
            op.create_unique_constraint(
                "uq_overtimes_user_date_source",
                "overtimes",
                ["user_id", "work_date", "source"],
            )

    # 3) Retirer le server_default
    #    -> Sous SQLite on L’IGNORE (pas d’ALTER supporté)
    if bind.dialect.name != "sqlite":
        op.alter_column(
            "overtimes",
            "source",
            server_default=None,
            existing_type=sa.Text(),
            existing_nullable=False,
        )


def downgrade():
    from alembic import op
    import sqlalchemy as sa

    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Supprimer l’unicité
    if bind.dialect.name == "sqlite":
        existing_idx = {ix["name"] for ix in insp.get_indexes("overtimes")}
        if "uq_overtimes_user_date_source" in existing_idx:
            op.drop_index("uq_overtimes_user_date_source", table_name="overtimes")
    else:
        try:
            uqs = insp.get_unique_constraints("overtimes")
            has_uq = any(uq.get("name") == "uq_overtimes_user_date_source" for uq in uqs)
        except NotImplementedError:
            has_uq = True
        if has_uq:
            op.drop_constraint("uq_overtimes_user_date_source", "overtimes", type_="unique")

    # Supprimer la colonne si présente
    cols = {c["name"] for c in insp.get_columns("overtimes")}
    if "source" in cols:
        op.drop_column("overtimes", "source")
