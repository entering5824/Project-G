"""Persist planner configs and human ranking feedback."""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision = "0003_planner_review"
down_revision = "0002_character_config"
branch_labels = None
depends_on = None

BASELINE = {
    "weights": {"deficiency": 0.32, "importance": 0.28, "tier": 0.18, "team": 0.12, "completion": 0.10},
    "tierFallback": 0.70, "teamSaved": 1.00, "teamNone": 0.50,
    "priorityOverride": {"normal": 1.00, "prioritized": 1.15, "deprioritized": 0.85},
    "completionNearThreshold": 0.75, "horizon": 20, "reorderThreshold": 3.0,
}

def upgrade():
    op.create_table("planner_config_versions",
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("planner_feedback",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planner_context_hash", sa.String(), nullable=False),
        sa.Column("goal_key", sa.String(), nullable=False),
        sa.Column("character_key", sa.String(), nullable=False),
        sa.Column("goal_type", sa.String(), nullable=False),
        sa.Column("tier_key", sa.String()),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rating", sa.String(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("score_breakdown_json", sa.JSON(), nullable=False),
        sa.Column("current_json", sa.JSON(), nullable=False),
        sa.Column("target_json", sa.JSON(), nullable=False))
    op.create_index("ix_planner_feedback_account_id", "planner_feedback", ["account_id"])
    op.create_index("ix_planner_feedback_context_hash", "planner_feedback", ["planner_context_hash"])
    op.create_index("ix_planner_feedback_goal_key", "planner_feedback", ["goal_key"])
    op.bulk_insert(sa.table("planner_config_versions",
        sa.column("version", sa.Integer()), sa.column("config_json", sa.JSON()), sa.column("created_at", sa.DateTime(timezone=True))),
        [{"version": 1, "config_json": BASELINE, "created_at": datetime.now(timezone.utc)}])

def downgrade():
    op.drop_index("ix_planner_feedback_goal_key", table_name="planner_feedback")
    op.drop_index("ix_planner_feedback_context_hash", table_name="planner_feedback")
    op.drop_index("ix_planner_feedback_account_id", table_name="planner_feedback")
    op.drop_table("planner_feedback")
    op.drop_table("planner_config_versions")
