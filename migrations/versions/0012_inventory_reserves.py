"""Persist account inventory reserves used by planner allocation."""
from alembic import op
import sqlalchemy as sa

revision = "0012_inventory_reserves"
down_revision = "0011_target_presets"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_reserves",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("material_key", sa.String(), primary_key=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("inventory_reserves")
