"""Persist Today pursuit/pin state and reproducible PlanRun records."""

from alembic import op
import sqlalchemy as sa

revision = "0013_plan_runs_today_state"
down_revision = "0012_inventory_reserves"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "today_state",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("pursued_task_id", sa.String(), nullable=True),
        sa.Column("pursued_character_key", sa.String(), nullable=True),
        sa.Column("pursued_score", sa.Float(), nullable=True),
        sa.Column("ordering_group", sa.String(), nullable=True),
        sa.Column("pursued_config_version", sa.String(), nullable=True),
        sa.Column("pinned_character_key", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "plan_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("snapshot_id", sa.String(), nullable=True),
        sa.Column("normalized_input_json", sa.JSON(), nullable=False),
        sa.Column("target_versions_json", sa.JSON(), nullable=False),
        sa.Column("inventory_version", sa.Integer(), nullable=False),
        sa.Column("planner_config_version", sa.String(), nullable=False),
        sa.Column("source_availability_json", sa.JSON(), nullable=False),
        sa.Column("context_json", sa.JSON(), nullable=False),
        sa.Column("hysteresis_state_json", sa.JSON(), nullable=False),
        sa.Column("engine_version", sa.String(), nullable=False),
        sa.Column("game_data_version", sa.String(), nullable=True),
        sa.Column("rv_formula_version", sa.String(), nullable=False),
        sa.Column("switch_threshold", sa.Float(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_plan_runs_account_id", "plan_runs", ["account_id"])
    op.create_index("ix_plan_runs_created_at", "plan_runs", ["created_at"])


def downgrade():
    op.drop_index("ix_plan_runs_created_at", table_name="plan_runs")
    op.drop_index("ix_plan_runs_account_id", table_name="plan_runs")
    op.drop_table("plan_runs")
    op.drop_table("today_state")
