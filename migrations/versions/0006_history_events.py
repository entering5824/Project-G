"""Persist structured snapshot, config, and derived history events."""
from alembic import op
import sqlalchemy as sa

revision = "0006_history_events"
down_revision = "0005_artifact_intelligence"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "history_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("snapshot_id", sa.String(), nullable=True),
        sa.Column("character_key", sa.String(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_history_events_account_id", "history_events", ["account_id"])
    op.create_index("ix_history_events_created_at", "history_events", ["created_at"])
    op.create_index("ix_history_events_event_type", "history_events", ["event_type"])
    op.create_index("ix_history_events_snapshot_id", "history_events", ["snapshot_id"])
    op.create_index("ix_history_events_character_key", "history_events", ["character_key"])


def downgrade():
    op.drop_table("history_events")
