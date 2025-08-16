
from alembic import op
import sqlalchemy as sa

revision = "0002_attendance"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("attendances",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("work_date", sa.Date, nullable=False, index=True),
        sa.Column("check_in", sa.DateTime),
        sa.Column("check_out", sa.DateTime),
        sa.Column("late_minutes", sa.Float, server_default="0"),
        sa.Column("total_hours", sa.Float, server_default="0"),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column("source", sa.String(20)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_attendance_user_date", "attendances", ["user_id", "work_date"])

def downgrade():
    op.drop_index("ix_attendance_user_date", table_name="attendances")
    op.drop_table("attendances")
