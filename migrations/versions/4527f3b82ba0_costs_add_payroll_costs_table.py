from alembic import op
import sqlalchemy as sa

# IDs
revision = "4527f3b82ba0"
down_revision = "39b21559ee9e"   # ← mets ici le head actuel (chez toi: le merge 39b21559ee9e)
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "payroll_costs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False, index=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("base_salary",   sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("overtime_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("leave_cost",    sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("benefits_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="XOF"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(datetime('now'))")),
        sa.UniqueConstraint("department_id", "year", "month", name="uq_payroll_costs_dep_month"),
    )
    op.create_index("ix_payroll_costs_year_month", "payroll_costs", ["year", "month"])

def downgrade():
    op.drop_index("ix_payroll_costs_year_month", table_name="payroll_costs")
    op.drop_table("payroll_costs")
