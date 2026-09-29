"""Persist local server, Resin, weekly, and temporary availability settings."""

from alembic import op
import sqlalchemy as sa

revision = "0015_account_availability_settings"
down_revision = "0014_planner_teams"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("game_language", sa.String(), nullable=False, server_default="en"))
    op.add_column("accounts", sa.Column("world_level", sa.Integer(), nullable=False, server_default="8"))
    op.add_column("accounts", sa.Column("resin", sa.Integer(), nullable=True))
    op.add_column("accounts", sa.Column("weekly_claimed_json", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("accounts", sa.Column("unavailable_sources_json", sa.JSON(), nullable=False, server_default="[]"))


def downgrade():
    op.drop_column("accounts", "unavailable_sources_json")
    op.drop_column("accounts", "weekly_claimed_json")
    op.drop_column("accounts", "resin")
    op.drop_column("accounts", "world_level")
    op.drop_column("accounts", "game_language")
