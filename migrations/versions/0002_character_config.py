"""Versioned character targets, tiers, assignments, and priority overrides."""
from alembic import op
import sqlalchemy as sa

revision = "0002_character_config"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("character_target_versions",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("character_key", sa.String(), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("target_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("tier_config_versions",
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("tiers_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("tier_assignment_versions",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("character_key", sa.String(), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("tier_key", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("character_priorities",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("character_key", sa.String(), primary_key=True),
        sa.Column("override", sa.String(), nullable=False, server_default="NORMAL"))

def downgrade():
    op.drop_table("character_priorities")
    op.drop_table("tier_assignment_versions")
    op.drop_table("tier_config_versions")
    op.drop_table("character_target_versions")
