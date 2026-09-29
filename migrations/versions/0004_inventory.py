"""Persist account material inventory independently from GOOD snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "0004_inventory"
down_revision = "0003_planner_review"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_entries",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("material_key", sa.String(), primary_key=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="MANUAL"),
        sa.CheckConstraint("quantity IS NULL OR quantity >= 0", name="ck_inventory_quantity_nonnegative"),
    )
    op.create_table(
        "inventory_state",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("inventory_state")
    op.drop_table("inventory_entries")
