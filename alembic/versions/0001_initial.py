
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    role_enum = sa.Enum("ADMIN","MANAGER","EMPLOYEE", name="role")
    role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table("departments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table("users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("department_id", sa.Integer, sa.ForeignKey("departments.id")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("last_name", sa.String(80), nullable=False),
        sa.Column("role", role_enum, nullable=False, server_default="EMPLOYEE"),
        sa.Column("hourly_rate", sa.Float, server_default="8"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table("users")
    op.drop_table("departments")
    op.execute("DROP TYPE IF EXISTS role")
