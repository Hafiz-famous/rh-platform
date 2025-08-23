from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = "76eb22c110c6"
down_revision = "a2ac94c154f3"  # <- celui juste avant dans ta chaîne
branch_labels = None
depends_on = None

def upgrade():
    # no-op: ce stub sert juste à rétablir la chaîne de révisions
    pass

def downgrade():
    pass
