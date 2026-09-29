"""Store editable planner teams separately from immutable GOOD observations."""

from alembic import op
import sqlalchemy as sa

revision = "0014_planner_teams"
down_revision = "0013_plan_runs_today_state"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "planner_teams",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("team_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("members_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("planner_teams")
