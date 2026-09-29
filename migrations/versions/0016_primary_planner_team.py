"""Allow one configured planner team to be marked as the primary team."""

from alembic import op
import sqlalchemy as sa

revision = "0016_primary_planner_team"
down_revision = "0015_account_availability_settings"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("planner_teams", sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("planner_teams", "is_primary")
