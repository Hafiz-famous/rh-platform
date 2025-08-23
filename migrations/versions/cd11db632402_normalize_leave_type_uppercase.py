from alembic import op
import sqlalchemy as sa

revision = "cd11db632402"
down_revision = "76eb22c110c6"
branch_labels = None
depends_on = None

def upgrade():
    # no-op; la normalisation a déjà été faite depuis l'appli/SQL manuel
    pass

def downgrade():
    pass
