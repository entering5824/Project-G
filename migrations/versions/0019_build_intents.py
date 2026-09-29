"""Persist per-account personal and Theater build intents."""
from alembic import op
import sqlalchemy as sa

revision = "0019_build_intents"
down_revision = "0018_tier_pack"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("account_planning_intents",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("personal_json", sa.JSON(), nullable=False),
        sa.Column("theater_json", sa.JSON(), nullable=False))


def downgrade():
    op.drop_table("account_planning_intents")
